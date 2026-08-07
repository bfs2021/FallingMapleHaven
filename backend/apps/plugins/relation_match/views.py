from __future__ import annotations

from typing import Any, cast

from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.common.utils import api_response, safe_int
from apps.plugins.utils import ensure_plugin_active
from .catalog import RELATION_TYPES
from .models import (
    RelationMatchPairResult,
    RelationMatchProfile,
    RelationMatchTest,
    RelationMatchTestAnswer,
    RelationMatchTestAnswerItem,
)
from .serializers import (
    RelationMatchCurrentTestSerializer,
    RelationMatchHomeProfileSerializer,
    RelationMatchPairResultDetailSerializer,
    RelationMatchProfileSummarySerializer,
)
from .services import (
    create_or_get_pair_result,
    create_plugin_notifications,
    get_current_test,
    get_or_create_visitor_identity,
    get_or_create_profile,
    resolve_submission_context,
    score_answers,
    set_visitor_cookie,
)

User = get_user_model()


def _response_with_cookie(response, request):
    if getattr(request, "_relation_match_visitor_token", None):
        set_visitor_cookie(response, request._relation_match_visitor_token)
    return response


def _ensure_visitor_cookie(request):
    token, token_hash, created = get_or_create_visitor_identity(request)
    request._relation_match_visitor_token = token
    request._relation_match_visitor_hash = token_hash
    request._relation_match_visitor_created = created
    return token, token_hash, created


class RelationMatchHomeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, owner_id):
        inactive = ensure_plugin_active("relation_match")
        if inactive:
            return inactive
        if not User.objects.filter(pk=owner_id).exists():
            return api_response(code=40004, message="用户不存在", status=status.HTTP_404_NOT_FOUND)

        profile = RelationMatchProfile.objects.filter(user_id=owner_id, test__slug="current").first()
        if profile is None:
            response_data = {
                "has_profile": False,
                "profile": None,
                "entry_text": "看看你们像什么",
                "start_test_url": f"/profile/{owner_id}/plugins/relation-match/tests/current/",
                "share_code": None,
                "share_url": None,
                "next_action": "invite",
                "history": {"total": 0, "page": 1, "page_size": 20, "results": []},
            }
            response = api_response(data=response_data)
            return _response_with_cookie(response, request)

        response_data = {
            "has_profile": True,
            "profile": RelationMatchHomeProfileSerializer(profile).data,
            "entry_text": "看看你们像什么",
            "start_test_url": f"/profile/{owner_id}/plugins/relation-match/tests/current/",
            "share_code": profile.share_code,
            "share_url": f"/profile/{owner_id}/plugins/relation-match?shareCode={profile.share_code}",
            "next_action": "invite",
            "history": {"total": 0, "page": 1, "page_size": 20, "results": []},
        }
        if request.user.is_authenticated and request.user.id == owner_id:
            pairs = RelationMatchPairResult.objects.filter(
                profile_a__user_id=owner_id
            ) | RelationMatchPairResult.objects.filter(profile_b__user_id=owner_id)
            pairs = pairs.order_by("-created_at").distinct()
            history_items = []
            for result in pairs:
                profile_a_user_id = getattr(result.profile_a, "user_id", None)
                other = result.profile_b if profile_a_user_id == owner_id else result.profile_a
                other_name = getattr(other, "participant_name", "")
                result_id = getattr(result, "id", None)
                history_items.append({
                    "pair_id": result_id,
                    "relation_type_name": RELATION_TYPES[str(result.relation_type)]["name"],
                    "subtitle": result.subtitle,
                    "other_participant_name": other_name,
                    "result_url": f"/profile/{owner_id}/plugins/relation-match/pairs/{result_id}/",
                    "created_at": result.created_at,
                })
            response_data["history"] = {"total": len(history_items), "page": 1, "page_size": 20, "results": history_items}
            if history_items:
                response_data["next_action"] = "match"
        response = api_response(data=response_data)
        return _response_with_cookie(response, request)


class RelationMatchCurrentTestView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        inactive = ensure_plugin_active("relation_match")
        if inactive:
            return inactive
        try:
            test = get_current_test()
        except ObjectDoesNotExist:
            return api_response(code=40004, message="测试不存在或不可用", status=status.HTTP_404_NOT_FOUND)

        _ensure_visitor_cookie(request)
        serializer = RelationMatchCurrentTestSerializer(test)
        response = api_response(data=serializer.data)
        return _response_with_cookie(response, request)


class RelationMatchCurrentTestSubmissionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        inactive = ensure_plugin_active("relation_match")
        if inactive:
            return inactive
        try:
            test = get_current_test()
        except ObjectDoesNotExist:
            return api_response(code=40004, message="测试不存在或不可用", status=status.HTTP_404_NOT_FOUND)

        participant_name = request.data.get("participant_name")
        context, visitor_meta = resolve_submission_context(request, participant_name)
        if context is None:
            assert visitor_meta is not None
            token, _token_hash, _created, message = visitor_meta
            request._relation_match_visitor_token = token
            if message:
                response = api_response(code=40001, message=message, status=status.HTTP_400_BAD_REQUEST)
                return _response_with_cookie(response, request)
            return api_response(code=40001, message="昵称不能为空", status=status.HTTP_400_BAD_REQUEST)
        if context.participant_type == "visitor":
            assert visitor_meta is not None
            request._relation_match_visitor_token = visitor_meta[0]

        raw_answers = request.data.get("answers")
        if not isinstance(raw_answers, list):
            return api_response(code=40001, message="答案格式错误", status=status.HTTP_400_BAD_REQUEST)
        if len(raw_answers) != 40:
            return api_response(code=40001, message="必须正好提交 40 题答案", status=status.HTTP_400_BAD_REQUEST)

        share_code = str(request.data.get("share_code", "")).strip()
        other_profile = None
        if share_code:
            try:
                other_profile = RelationMatchProfile.objects.get(share_code=share_code, test=test)
            except ObjectDoesNotExist:
                return api_response(code=40004, message="分享码不存在", status=status.HTTP_404_NOT_FOUND)

        if request.user.is_authenticated:
            if RelationMatchProfile.objects.filter(user=request.user, test=test).exists():
                return api_response(code=40005, message="你已经提交过这套测试", data={"leaderboard_url": f"/profile/{request.user.id}/plugins/relation-match"}, status=status.HTTP_400_BAD_REQUEST)
        elif RelationMatchProfile.objects.filter(visitor_token_hash=context.visitor_token_hash, test=test).exists():
            return api_response(code=40005, message="你已经提交过这套测试", data={"leaderboard_url": "/plugins/relation-match"}, status=status.HTTP_400_BAD_REQUEST)

        if other_profile is not None:
            if request.user.is_authenticated and other_profile.user_id == request.user.id:
                return api_response(code=40005, message="不能和自己生成关系结果", status=status.HTTP_400_BAD_REQUEST)
            if (not request.user.is_authenticated) and other_profile.visitor_token_hash == context.visitor_token_hash:
                return api_response(code=40005, message="不能和自己生成关系结果", status=status.HTTP_400_BAD_REQUEST)

        answer_map: dict[int, list[int]] = {}
        try:
            for raw in raw_answers:
                if not isinstance(raw, dict):
                    raise ValueError("答案格式错误")
                question_id = int(raw.get("question_id"))
                selected_ids = raw.get("selected_option_ids")
                if isinstance(selected_ids, list):
                    option_ids = [int(option_id) for option_id in selected_ids]
                else:
                    option_ids = [int(raw.get("selected_option_id"))]
                answer_map[question_id] = option_ids
        except (TypeError, ValueError):
            return api_response(code=40001, message="答案格式错误", status=status.HTTP_400_BAD_REQUEST)

        try:
            dimension_scores, answer_items = score_answers(test, answer_map)
        except ValueError as exc:
            return api_response(code=40001, message=str(exc), status=status.HTTP_400_BAD_REQUEST, data={"errors": [{"message": str(exc)}]})

        atomic_context: Any = transaction.atomic
        try:
            with atomic_context():
                answer = RelationMatchTestAnswer.objects.create(
                    test=test,
                    participant_type=context.participant_type,
                    user=context.user,
                    participant_name=context.participant_name,
                    visitor_token_hash=context.visitor_token_hash,
                )
                for item in answer_items:
                    RelationMatchTestAnswerItem.objects.create(answer=answer, **item)

                profile = get_or_create_profile(test, context, dimension_scores)
                pair_result = None
                if other_profile is not None:
                    pair_result, created = create_or_get_pair_result(profile, other_profile)
                    if created:
                        create_plugin_notifications(pair_result, profile)
        except IntegrityError:
            answer_exists = RelationMatchTestAnswer.objects.filter(
                test=test,
                participant_type=context.participant_type,
                user=context.user,
                visitor_token_hash=context.visitor_token_hash,
                is_deleted=False,
            ).exists()
            profile_exists = RelationMatchProfile.objects.filter(
                test=test,
                participant_type=context.participant_type,
                user=context.user,
                visitor_token_hash=context.visitor_token_hash,
            ).exists()
            if not answer_exists and not profile_exists:
                raise
            return api_response(
                code=40005,
                message="你已经提交过这套测试",
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile_user_id = getattr(profile, "user_id", None)
        profile_id = getattr(profile, "id", None)
        share_url = f"/profile/{profile_user_id or profile_id}/plugins/relation-match?shareCode={profile.share_code}"
        profile_payload = RelationMatchProfileSummarySerializer(profile).data
        data = {
            "profile": profile_payload,
            "next_action": "match" if pair_result else "invite",
            "share_code": profile.share_code,
            "share_url": share_url,
            "pair": RelationMatchPairResultDetailSerializer(pair_result).data if pair_result else None,
        }
        response = api_response(data=data, status=status.HTTP_201_CREATED)
        return _response_with_cookie(response, request)


class RelationMatchShareMatchView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, share_code):
        inactive = ensure_plugin_active("relation_match")
        if inactive:
            return inactive
        if request.user.is_authenticated:
            current_profile = RelationMatchProfile.objects.filter(user_id=request.user.id, test__slug="current").first()
        else:
            _, token_hash, _ = _ensure_visitor_cookie(request)
            current_profile = RelationMatchProfile.objects.filter(visitor_token_hash=token_hash).first()

        if current_profile is None:
            return api_response(code=40004, message="请先完成测试", status=status.HTTP_404_NOT_FOUND)

        try:
            other_profile = RelationMatchProfile.objects.get(share_code=share_code)
        except ObjectDoesNotExist:
            return api_response(code=40004, message="分享码不存在", status=status.HTTP_404_NOT_FOUND)

        if other_profile.id == current_profile.id:
            return api_response(code=40005, message="不能和自己生成关系结果", status=status.HTTP_400_BAD_REQUEST)

        atomic_context: Any = transaction.atomic
        with atomic_context():
            pair_result, created = create_or_get_pair_result(current_profile, other_profile)
            if created:
                create_plugin_notifications(pair_result, current_profile)

        serializer = RelationMatchPairResultDetailSerializer(pair_result)
        response = api_response(data=serializer.data)
        return _response_with_cookie(response, request)


class RelationMatchPairDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, result_id):
        inactive = ensure_plugin_active("relation_match")
        if inactive:
            return inactive
        try:
            result = RelationMatchPairResult.objects.select_related("profile_a", "profile_b").get(pk=result_id)
        except ObjectDoesNotExist:
            return api_response(code=40004, message="结果不存在", status=status.HTTP_404_NOT_FOUND)
        response = api_response(data=RelationMatchPairResultDetailSerializer(result).data)
        return _response_with_cookie(response, request)


class RelationMatchMyPairsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        inactive = ensure_plugin_active("relation_match")
        if inactive:
            return inactive
        profiles = RelationMatchProfile.objects.filter(user=request.user)
        if not profiles.exists():
            return api_response(data={"total": 0, "page": 1, "page_size": 20, "results": []})
        profile_ids = list(profiles.values_list("id", flat=True))
        queryset = RelationMatchPairResult.objects.filter(profile_a_id__in=profile_ids) | RelationMatchPairResult.objects.filter(profile_b_id__in=profile_ids)
        queryset = queryset.select_related("profile_a", "profile_b").order_by("-created_at").distinct()
        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = []
        for result in queryset[start:end]:
            profile_a_user_id = getattr(result.profile_a, "user_id", None)
            other = result.profile_b if profile_a_user_id == request.user.id else result.profile_a
            other_name = getattr(other, "participant_name", "")
            result_id = getattr(result, "id", None)
            items.append({
                "pair_id": result_id,
                "relation_type_name": RELATION_TYPES[str(result.relation_type)]["name"],
                "subtitle": result.subtitle,
                "other_participant_name": other_name,
                "result_url": f"/profile/{request.user.id}/plugins/relation-match/pairs/{result_id}/",
                "created_at": result.created_at,
            })
        return api_response(data={"total": total, "page": page, "page_size": page_size, "results": items})

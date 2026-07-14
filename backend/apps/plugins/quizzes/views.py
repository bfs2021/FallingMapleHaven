import hashlib
import secrets

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.common.utils import api_response
from apps.notifications.models import Notification
from apps.plugins.utils import ensure_plugin_active
from .models import (
    MAX_OPTIONS_PER_QUESTION,
    MIN_OPTIONS_PER_QUESTION,
    PUBLISHED_QUESTION_COUNT,
    QuizQuestionBank,
    QuizSubmission,
    QuizSubmissionAnswer,
    QuizTest,
    QuizTestOption,
    QuizTestQuestion,
)
from .serializers import (
    QuizBankQuestionSerializer,
    QuizSubmissionSummarySerializer,
    QuizTestCardSerializer,
    QuizTestDetailOwnerSerializer,
    QuizTestDetailPublicSerializer,
)
from .utils import filter_question_bank_by_tag

User = get_user_model()
VISITOR_COOKIE_NAME = "fmh_visitor_id"
VISITOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 365


def _paginate(queryset, request, serializer_class, context=None):
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = max(1, min(100, int(request.query_params.get("page_size", 20))))
    except (TypeError, ValueError):
        page_size = 20
    total = queryset.count() if hasattr(queryset, "count") and not isinstance(queryset, list) else len(queryset)
    start = (page - 1) * page_size
    end = start + page_size
    serializer = serializer_class(queryset[start:end], many=True, context=context or {})
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": serializer.data,
    }


def _hash_visitor_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _get_or_create_visitor_token(request):
    token = request.COOKIES.get(VISITOR_COOKIE_NAME)
    created = False
    if not token:
        token = secrets.token_urlsafe(32)
        created = True
    return token, _hash_visitor_token(token), created


def _set_visitor_cookie(response, token):
    response.set_cookie(
        VISITOR_COOKIE_NAME,
        token,
        max_age=VISITOR_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
    )
    return response


def _visitor_response(response, token, created):
    if created:
        _set_visitor_cookie(response, token)
    return response


def _leaderboard_url(test, submission):
    return f"/profile/{test.owner_id}/plugins/quiz/tests/{test.id}/leaderboard?answerId={submission.id}"


def _title_for_score(correct_count):
    if correct_count == 10:
        return "灵魂拍档"
    if correct_count >= 8:
        return "很懂 TA"
    if correct_count >= 6:
        return "默契在线"
    if correct_count >= 4:
        return "还要多聊聊"
    return "神秘距离感"


def _current_submission_for_request(request, test, answer_id=None):
    submissions = QuizSubmission.objects.filter(test=test, is_deleted=False)
    if answer_id:
        try:
            return submissions.get(pk=answer_id)
        except (QuizSubmission.DoesNotExist, ValueError, TypeError):
            return None
    if request.user.is_authenticated:
        return submissions.filter(user=request.user, participant_type=QuizSubmission.ParticipantType.USER).first()
    token = request.COOKIES.get(VISITOR_COOKIE_NAME)
    if not token:
        return None
    return submissions.filter(
        visitor_token_hash=_hash_visitor_token(token),
        participant_type=QuizSubmission.ParticipantType.VISITOR,
    ).first()


def _submission_context_for_tests(request, tests):
    ids = [test.id for test in tests]
    if not ids:
        return set(), {}
    queryset = QuizSubmission.objects.filter(test_id__in=ids, is_deleted=False)
    if request.user.is_authenticated:
        queryset = queryset.filter(user=request.user, participant_type=QuizSubmission.ParticipantType.USER)
    else:
        token = request.COOKIES.get(VISITOR_COOKIE_NAME)
        if not token:
            return set(), {}
        queryset = queryset.filter(
            visitor_token_hash=_hash_visitor_token(token),
            participant_type=QuizSubmission.ParticipantType.VISITOR,
        )
    submission_map = {item.test_id: item.id for item in queryset}
    return set(submission_map.keys()), submission_map


def _rank_submissions(submissions, current_submission_id=None):
    ranked = []
    previous_score = None
    previous_rank = 0
    score_counts = {}
    for submission in submissions:
        score_counts[submission.score_percent] = score_counts.get(submission.score_percent, 0) + 1
    for index, submission in enumerate(submissions, 1):
        if previous_score is None or submission.score_percent != previous_score:
            previous_rank = index
            previous_score = submission.score_percent
        submission.rank = previous_rank
        submission.is_tied = score_counts[submission.score_percent] > 1
        submission.total_count = PUBLISHED_QUESTION_COUNT
        submission.is_current = submission.id == current_submission_id
        ranked.append(submission)
    return ranked


def _field_error(field, message):
    return {"field": field, "message": message}


def _validate_and_normalize_questions(raw_questions, *, strict_publish=False):
    errors = []
    normalized = []
    raw_questions = raw_questions or []

    if strict_publish and len(raw_questions) != PUBLISHED_QUESTION_COUNT:
        errors.append(_field_error("questions", "必须正好 10 道题"))

    seen_orders = set()
    for index, raw in enumerate(raw_questions):
        order = raw.get("order", index + 1)
        try:
            order = int(order)
        except (TypeError, ValueError):
            errors.append(_field_error(f"questions[{index}].order", f"第 {index + 1} 题顺序非法"))
            order = index + 1
        if order in seen_orders:
            errors.append(_field_error(f"questions[{index}].order", f"第 {index + 1} 题顺序重复"))
        seen_orders.add(order)

        question_text = str(raw.get("question_text", "")).strip()
        if strict_publish and not question_text:
            errors.append(_field_error(f"questions[{index}].question_text", f"第 {index + 1} 题题目不能为空"))
        if len(question_text) > 80:
            errors.append(_field_error(f"questions[{index}].question_text", f"第 {index + 1} 题题目不能超过 80 个字符"))

        raw_options = raw.get("options") or []
        if strict_publish and not (MIN_OPTIONS_PER_QUESTION <= len(raw_options) <= MAX_OPTIONS_PER_QUESTION):
            errors.append(_field_error(f"questions[{index}].options", f"第 {index + 1} 题必须有 2-4 个选项"))
        if len(raw_options) > MAX_OPTIONS_PER_QUESTION:
            errors.append(_field_error(f"questions[{index}].options", f"第 {index + 1} 题最多 4 个选项"))

        options = []
        option_orders = set()
        for option_index, option_raw in enumerate(raw_options):
            option_order = option_raw.get("order", option_index + 1)
            try:
                option_order = int(option_order)
            except (TypeError, ValueError):
                errors.append(_field_error(f"questions[{index}].options[{option_index}].order", "选项顺序非法"))
                option_order = option_index + 1
            if option_order in option_orders:
                errors.append(_field_error(f"questions[{index}].options[{option_index}].order", "选项顺序重复"))
            option_orders.add(option_order)
            option_text = str(option_raw.get("option_text", "")).strip()
            if strict_publish and not option_text:
                errors.append(_field_error(f"questions[{index}].options[{option_index}].option_text", "选项不能为空"))
            if len(option_text) > 30:
                errors.append(_field_error(f"questions[{index}].options[{option_index}].option_text", "选项不能超过 30 个字符"))
            options.append({"option_text": option_text, "order": option_order})

        correct_order = raw.get("correct_option_order")
        if correct_order in (None, ""):
            correct_order = None
        else:
            try:
                correct_order = int(correct_order)
            except (TypeError, ValueError):
                errors.append(_field_error(f"questions[{index}].correct_option", f"第 {index + 1} 题标准答案非法"))
                correct_order = None
        if strict_publish and correct_order is None:
            errors.append(_field_error(f"questions[{index}].correct_option", f"第 {index + 1} 题必须设置标准答案"))
        if correct_order is not None and correct_order not in option_orders:
            errors.append(_field_error(f"questions[{index}].correct_option", f"第 {index + 1} 题标准答案必须属于该题选项"))

        normalized.append({
            "question_text": question_text,
            "order": order,
            "correct_option_order": correct_order,
            "source_bank_question_id": raw.get("source_bank_question_id"),
            "options": options,
        })
    return normalized, errors


def _replace_test_questions(test, normalized_questions):
    test.questions.update(correct_option=None)
    test.questions.all().delete()
    for question_data in normalized_questions:
        source_id = question_data.get("source_bank_question_id")
        if source_id and not QuizQuestionBank.objects.filter(pk=source_id).exists():
            source_id = None
        question = QuizTestQuestion.objects.create(
            test=test,
            question_type=QuizTestQuestion.Type.SINGLE_CHOICE,
            question_text=question_data["question_text"],
            order=question_data["order"],
            source_bank_question_id=source_id,
        )
        created_options = {}
        for option_data in question_data["options"]:
            option = QuizTestOption.objects.create(question=question, **option_data)
            created_options[option.order] = option
        correct_order = question_data.get("correct_option_order")
        if correct_order in created_options:
            question.correct_option = created_options[correct_order]
            question.save(update_fields=["correct_option"])


class PublicQuizTestsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, owner_id):
        inactive = ensure_plugin_active("quiz")
        if inactive:
            return inactive
        if not User.objects.filter(pk=owner_id).exists():
            return api_response(code=40004, message="用户不存在", status=status.HTTP_404_NOT_FOUND)
        tests = QuizTest.objects.filter(owner_id=owner_id, status=QuizTest.Status.PUBLISHED).order_by("-published_at")
        page_data = _paginate(tests, request, QuizTestCardSerializer, {"request": request})
        start = (page_data["page"] - 1) * page_data["page_size"]
        end = page_data["page"] * page_data["page_size"]
        page_tests = list(tests[start:end])
        submitted_ids, _ = _submission_context_for_tests(request, page_tests)
        page_data["results"] = QuizTestCardSerializer(
            page_tests,
            many=True,
            context={"request": request, "submitted_test_ids": submitted_ids},
        ).data
        return api_response(data=page_data)


class MyQuizTestsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        inactive = ensure_plugin_active("quiz")
        if inactive:
            return inactive
        tests = QuizTest.objects.filter(owner=request.user).exclude(status=QuizTest.Status.DELETED).order_by("-created_at")
        status_param = request.query_params.get("status")
        if status_param:
            tests = tests.filter(status=status_param)
        return api_response(data=_paginate(tests, request, QuizTestCardSerializer, {"request": request}))

    def post(self, request):
        inactive = ensure_plugin_active("quiz")
        if inactive:
            return inactive
        if QuizTest.objects.filter(owner=request.user).exclude(status=QuizTest.Status.DELETED).count() >= 3:
            return api_response(code=40005, message="每个主页主人最多创建 3 套测试", status=status.HTTP_400_BAD_REQUEST)
        title = str(request.data.get("title", "")).strip()
        if not title or len(title) > 30:
            return api_response(code=40001, message="测试标题不能为空且不超过 30 个字符", status=status.HTTP_400_BAD_REQUEST)
        test = QuizTest.objects.create(owner=request.user, title=title)
        normalized, errors = _validate_and_normalize_questions(request.data.get("questions") or [])
        if errors:
            test.delete()
            return api_response(
                code=40001,
                message="测试草稿保存失败",
                data={"errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _replace_test_questions(test, normalized)
        return api_response(data=QuizTestDetailOwnerSerializer(test).data, status=status.HTTP_201_CREATED)


class MyQuizTestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object_response(self, request, test_id):
        try:
            test = QuizTest.objects.get(pk=test_id)
        except QuizTest.DoesNotExist:
            return None, api_response(code=40004, message="测试不存在", status=status.HTTP_404_NOT_FOUND)
        if test.owner_id != request.user.id:
            return None, api_response(code=40003, message="无权限操作该测试", status=status.HTTP_403_FORBIDDEN)
        if test.status == QuizTest.Status.DELETED:
            return None, api_response(code=40004, message="测试不存在", status=status.HTTP_404_NOT_FOUND)
        return test, None

    def get(self, request, test_id):
        test, error_response = self.get_object_response(request, test_id)
        if error_response:
            return error_response
        return api_response(data=QuizTestDetailOwnerSerializer(test).data)

    def patch(self, request, test_id):
        test, error_response = self.get_object_response(request, test_id)
        if error_response:
            return error_response
        if test.status == QuizTest.Status.PUBLISHED:
            return api_response(code=40005, message="已发布测试不可编辑", status=status.HTTP_400_BAD_REQUEST)
        title = request.data.get("title")
        if title is not None:
            title = str(title).strip()
            if not title or len(title) > 30:
                return api_response(code=40001, message="测试标题不能为空且不超过 30 个字符", status=status.HTTP_400_BAD_REQUEST)
            test.title = title
        if "questions" in request.data:
            normalized, errors = _validate_and_normalize_questions(request.data.get("questions") or [])
            if errors:
                return api_response(
                    code=40001,
                    message="测试草稿保存失败",
                    data={"errors": errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            _replace_test_questions(test, normalized)
        test.save(update_fields=["title", "updated_at"])
        return api_response(data=QuizTestDetailOwnerSerializer(test).data)

    def delete(self, request, test_id):
        test, error_response = self.get_object_response(request, test_id)
        if error_response:
            return error_response
        test.status = QuizTest.Status.DELETED
        test.deleted_at = timezone.now()
        test.save(update_fields=["status", "deleted_at", "updated_at"])
        return api_response(data=None)


class PublishQuizTestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, test_id):
        try:
            test = QuizTest.objects.get(pk=test_id)
        except QuizTest.DoesNotExist:
            return api_response(code=40004, message="测试不存在", status=status.HTTP_404_NOT_FOUND)
        if test.owner_id != request.user.id:
            return api_response(code=40003, message="无权限操作该测试", status=status.HTTP_403_FORBIDDEN)
        if test.status == QuizTest.Status.DELETED:
            return api_response(code=40004, message="测试不存在", status=status.HTTP_404_NOT_FOUND)
        if test.status != QuizTest.Status.DRAFT:
            return api_response(code=40005, message="只有草稿测试可以发布", status=status.HTTP_400_BAD_REQUEST)

        raw_questions = []
        for question in test.questions.prefetch_related("options").order_by("order"):
            raw_questions.append({
                "question_text": question.question_text,
                "order": question.order,
                "correct_option_order": question.correct_option.order if question.correct_option_id else None,
                "source_bank_question_id": question.source_bank_question_id,
                "options": [
                    {"option_text": option.option_text, "order": option.order}
                    for option in question.options.order_by("order")
                ],
            })
        _, errors = _validate_and_normalize_questions(raw_questions, strict_publish=True)
        if errors:
            return api_response(
                code=40001,
                message="测试发布校验失败",
                data={"errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        test.status = QuizTest.Status.PUBLISHED
        test.published_at = timezone.now()
        test.save(update_fields=["status", "published_at", "updated_at"])
        return api_response(data=QuizTestDetailOwnerSerializer(test).data)


class PublicQuizTestDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, test_id):
        try:
            test = QuizTest.objects.get(pk=test_id, status=QuizTest.Status.PUBLISHED)
        except QuizTest.DoesNotExist:
            return api_response(code=40004, message="测试不存在", status=status.HTTP_404_NOT_FOUND)
        submitted_ids, submission_map = _submission_context_for_tests(request, [test])
        response = api_response(data=QuizTestDetailPublicSerializer(
            test,
            context={
                "request": request,
                "submitted_test_ids": submitted_ids,
                "submission_map": submission_map,
            },
        ).data)
        if not request.user.is_authenticated:
            token, _, created = _get_or_create_visitor_token(request)
            if created:
                _set_visitor_cookie(response, token)
        return response


class SubmitQuizTestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, test_id):
        try:
            test = QuizTest.objects.select_related("owner").get(pk=test_id, status=QuizTest.Status.PUBLISHED)
        except QuizTest.DoesNotExist:
            return api_response(code=40004, message="测试不存在", status=status.HTTP_404_NOT_FOUND)
        if request.user.is_authenticated and request.user.is_staff:
            return api_response(code=40003, message="管理员不能参与测试", status=status.HTTP_403_FORBIDDEN)
        if request.user.is_authenticated and request.user.id == test.owner_id:
            return api_response(code=40005, message="不能参与自己的测试", status=status.HTTP_400_BAD_REQUEST)

        visitor_token = None
        visitor_hash = None
        visitor_created = False
        if request.user.is_authenticated:
            participant_type = QuizSubmission.ParticipantType.USER
            participant_name = request.user.nickname
            user = request.user
        else:
            participant_type = QuizSubmission.ParticipantType.VISITOR
            participant_name = str(request.data.get("participant_name", "")).strip()
            if not participant_name or len(participant_name) > 12:
                return api_response(code=40001, message="昵称不能为空，且不超过 12 个字符", status=status.HTTP_400_BAD_REQUEST)
            visitor_token, visitor_hash, visitor_created = _get_or_create_visitor_token(request)
            user = None

        existing = QuizSubmission.objects.filter(test=test, is_deleted=False)
        if user:
            existing = existing.filter(user=user, participant_type=QuizSubmission.ParticipantType.USER).first()
        else:
            existing = existing.filter(visitor_token_hash=visitor_hash, participant_type=QuizSubmission.ParticipantType.VISITOR).first()
        if existing:
            response = api_response(
                code=40005,
                message="你已经提交过这套测试",
                data={"submission_id": existing.id, "leaderboard_url": _leaderboard_url(test, existing)},
                status=status.HTTP_400_BAD_REQUEST,
            )
            return _visitor_response(response, visitor_token, visitor_created)

        answers = request.data.get("answers") or []
        if len(answers) != PUBLISHED_QUESTION_COUNT:
            response = api_response(code=40001, message="必须提交 10 道答案", status=status.HTTP_400_BAD_REQUEST)
            return _visitor_response(response, visitor_token, visitor_created)
        question_ids = [item.get("question_id") for item in answers]
        if len(set(question_ids)) != len(question_ids):
            response = api_response(code=40001, message="每题只能提交一次", status=status.HTTP_400_BAD_REQUEST)
            return _visitor_response(response, visitor_token, visitor_created)

        questions = {q.id: q for q in test.questions.select_related("correct_option").prefetch_related("options")}
        if set(question_ids) != set(questions.keys()):
            response = api_response(code=40001, message="提交题目不属于该测试", status=status.HTTP_400_BAD_REQUEST)
            return _visitor_response(response, visitor_token, visitor_created)
        options = QuizTestOption.objects.filter(question_id__in=question_ids)
        option_question_map = {option.id: option.question_id for option in options}

        normalized_answers = []
        correct_count = 0
        for item in answers:
            question_id = item.get("question_id")
            option_id = item.get("selected_option_id")
            if option_question_map.get(option_id) != question_id:
                response = api_response(code=40001, message="选项不属于对应题目", status=status.HTTP_400_BAD_REQUEST)
                return _visitor_response(response, visitor_token, visitor_created)
            is_correct = questions[question_id].correct_option_id == option_id
            if is_correct:
                correct_count += 1
            normalized_answers.append((questions[question_id], option_id, is_correct))

        score_percent = round((correct_count / PUBLISHED_QUESTION_COUNT) * 100, 2)
        try:
            with transaction.atomic():
                submission = QuizSubmission.objects.create(
                    test=test,
                    participant_type=participant_type,
                    user=user,
                    participant_name=participant_name,
                    visitor_token_hash=visitor_hash,
                    correct_count=correct_count,
                    score_percent=score_percent,
                    title=_title_for_score(correct_count),
                )
                QuizSubmissionAnswer.objects.bulk_create([
                    QuizSubmissionAnswer(
                        submission=submission,
                        question=question,
                        selected_option_id=option_id,
                        is_correct=is_correct,
                    )
                    for question, option_id, is_correct in normalized_answers
                ])
        except IntegrityError:
            existing = QuizSubmission.objects.filter(test=test, is_deleted=False)
            existing = existing.filter(user=user).first() if user else existing.filter(visitor_token_hash=visitor_hash).first()
            response = api_response(
                code=40005,
                message="你已经提交过这套测试",
                data={"submission_id": existing.id if existing else None, "leaderboard_url": _leaderboard_url(test, existing) if existing else None},
                status=status.HTTP_400_BAD_REQUEST,
            )
            return _visitor_response(response, visitor_token, visitor_created)

        if user:
            Notification.objects.create(
                recipient=test.owner,
                sender=user,
                notification_type=Notification.Type.PLUGIN_EVENT,
                title="有人完成了你的默契测试",
                content=f"{participant_name} 完成了《{test.title}》",
                link=_leaderboard_url(test, submission),
            )

        ranked = _rank_submissions(list(QuizSubmission.objects.filter(test=test, is_deleted=False).order_by("-score_percent", "created_at", "id")), submission.id)
        current = next(item for item in ranked if item.id == submission.id)
        response = api_response(
            data={
                "submission": QuizSubmissionSummarySerializer(current, context={"request": request}).data,
                "leaderboard_url": _leaderboard_url(test, submission),
            },
            status=status.HTTP_201_CREATED,
        )
        return _visitor_response(response, visitor_token, visitor_created)


class QuizTestLeaderboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, test_id):
        try:
            test = QuizTest.objects.get(pk=test_id, status=QuizTest.Status.PUBLISHED)
        except QuizTest.DoesNotExist:
            return api_response(code=40004, message="测试不存在", status=status.HTTP_404_NOT_FOUND)
        answer_id = request.query_params.get("answer_id") or request.query_params.get("answerId")
        current_submission = _current_submission_for_request(request, test, answer_id)
        submissions = list(QuizSubmission.objects.filter(test=test, is_deleted=False).order_by("-score_percent", "created_at", "id"))
        ranked = _rank_submissions(submissions, current_submission.id if current_submission else None)
        page_data = _paginate(ranked, request, QuizSubmissionSummarySerializer, {"request": request})
        return api_response(data={
            "test": {"id": test.id, "title": test.title, "owner": QuizTestCardSerializer(test).data["owner"]},
            "current_submission": QuizSubmissionSummarySerializer(current_submission, context={"request": request}).data if current_submission else None,
            "leaderboard": page_data,
        })


class MyQuizSubmissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        submissions = QuizSubmission.objects.filter(user=request.user, is_deleted=False).select_related("test", "test__owner").order_by("-created_at")
        page = _paginate(submissions, request, QuizSubmissionSummarySerializer, {"request": request})
        items = submissions[(page["page"] - 1) * page["page_size"]:page["page"] * page["page_size"]]
        page["results"] = [
            {
                "test": {
                    "id": item.test.id,
                    "title": item.test.title,
                    "owner": QuizTestCardSerializer(item.test).data["owner"],
                },
                "submission": {
                    "id": item.id,
                    "correct_count": item.correct_count,
                    "total_count": PUBLISHED_QUESTION_COUNT,
                    "score_percent": float(item.score_percent),
                    "title": item.title,
                    "created_at": item.created_at,
                },
                "leaderboard_url": _leaderboard_url(item.test, item),
            }
            for item in items
        ]
        return api_response(data=page)


class QuizQuestionBankView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bank = QuizQuestionBank.objects.all().order_by("-created_at")
        q = request.query_params.get("q")
        if q:
            bank = bank.filter(question_text__icontains=q)
        tag = request.query_params.get("tag", "").strip()
        bank = filter_question_bank_by_tag(bank, tag)
        return api_response(data=_paginate(bank, request, QuizBankQuestionSerializer, {"request": request}))

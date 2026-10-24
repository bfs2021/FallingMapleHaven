from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Any, cast

from django.contrib.auth import get_user_model
from ...notifications.models import Notification
from .catalog import (
    DIMENSIONS,
    RELATION_TYPES,
    build_dimension_max_raw_scores,
    build_user_short_summary,
    dimension_label,
)
from .models import (
    BASE_QUESTION_COUNT,
    RelationMatchPairResult,
    RelationMatchPairResultMember,
    RelationMatchProfile,
    RelationMatchQuestion,
    RelationMatchQuestionOption,
    RelationMatchTest,
    RelationMatchTestAnswer,
    RelationMatchTestAnswerItem,
)

User = get_user_model()


def hash_visitor_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def make_visitor_token() -> str:
    return secrets.token_urlsafe(32)


def make_share_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def make_share_token() -> str:
    return secrets.token_urlsafe(40)


def get_current_test() -> RelationMatchTest:
    return RelationMatchTest.objects.filter(slug="current", status=RelationMatchTest.Status.PUBLISHED).prefetch_related("questions__options").get()


def get_or_create_visitor_identity(request):
    token = request.COOKIES.get("fmh_relation_visitor_id")
    created = False
    if not token:
        token = make_visitor_token()
        created = True
    return token, hash_visitor_token(token), created


def set_visitor_cookie(response, token: str):
    response.set_cookie(
        "fmh_relation_visitor_id",
        token,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="Lax",
    )
    return response


@dataclass(frozen=True, slots=True)
class SubmissionContext:
    participant_type: str
    participant_name: str
    user: Any | None
    visitor_token_hash: str | None


def resolve_submission_context(request, participant_name: str | None):
    if request.user.is_authenticated:
        return SubmissionContext(
            participant_type="user",
            participant_name=request.user.nickname,
            user=request.user,
            visitor_token_hash=None,
        ), None

    visitor_token, visitor_hash, created = get_or_create_visitor_identity(request)
    if not participant_name or not participant_name.strip():
        return None, (visitor_token, visitor_hash, created, "昵称不能为空")
    return SubmissionContext(
        participant_type="visitor",
        participant_name=participant_name.strip()[:30],
        user=None,
        visitor_token_hash=visitor_hash,
    ), (visitor_token, visitor_hash, created, None)


MAX_RAW_SCORES = build_dimension_max_raw_scores()


def normalize_dimension_scores(raw_scores: dict[str, int]) -> dict[str, int]:
    """按 Docs/18 §6：每维原始分满分映射到 1-10，两端各留 1 分和 10 分。"""
    normalized: dict[str, int] = {}
    for dimension in DIMENSIONS:
        score = raw_scores.get(dimension, 0)
        max_raw = MAX_RAW_SCORES[dimension]
        normalized[dimension] = max(1, min(10, 1 + round(score * 9 / max_raw)))
    return normalized


def score_answers(test: RelationMatchTest, answer_map: dict[int, list[int]]):
    questions = list(cast(Any, test).questions.prefetch_related("options").order_by("order"))
    if len(questions) != BASE_QUESTION_COUNT:
        raise ValueError("测试题目数量不正确")

    raw_scores = {dimension: 0 for dimension in DIMENSIONS}
    answer_items = []
    for question in questions:
        selected_option_ids = answer_map.get(question.id)
        if not selected_option_ids:
            raise ValueError(f"第 {question.order} 题缺少答案")

        options = list(question.options.all().order_by("order"))
        option_id_map = {option.id: option for option in options}
        if question.question_type in {"single_choice", "either_or", "scale"}:
            if len(selected_option_ids) != 1:
                raise ValueError(f"第 {question.order} 题只能选择 1 个选项")
        elif len(selected_option_ids) < 1:
            raise ValueError(f"第 {question.order} 题至少选择 1 个选项")

        selected_options = []
        dimension_payload = {dimension: 0 for dimension in DIMENSIONS}
        for option_id in selected_option_ids:
            option = option_id_map.get(option_id)
            if option is None:
                raise ValueError(f"第 {question.order} 题存在无效选项")
            selected_options.append(option_id)
            for dimension, value in option.dimension_payload.items():
                raw_scores[dimension] = raw_scores.get(dimension, 0) + int(value)
                dimension_payload[dimension] = dimension_payload.get(dimension, 0) + int(value)

        answer_items.append(
            {
                "question": question,
                "selected_options": (
                    selected_options
                    if question.question_type == "multi_select" or len(selected_options) > 1
                    else selected_options[0]
                ),
                "dimension_payload": dimension_payload,
            }
        )

    return normalize_dimension_scores(raw_scores), answer_items


def build_profile_summary(participant_name: str, dimension_scores: dict[str, int]) -> str:
    return build_user_short_summary(dimension_scores)


def get_or_create_profile(test: RelationMatchTest, context: SubmissionContext, dimension_scores: dict[str, int]) -> RelationMatchProfile:
    if context.participant_type == "user":
        existing = RelationMatchProfile.objects.filter(user=context.user, participant_type=context.participant_type, test=test).first()
    else:
        existing = RelationMatchProfile.objects.filter(
            participant_type=context.participant_type,
            visitor_token_hash=context.visitor_token_hash,
            test=test,
        ).first()
    if existing:
        return existing

    share_code = make_share_code()
    while RelationMatchProfile.objects.filter(share_code=share_code).exists():
        share_code = make_share_code()

    share_token = make_share_token()
    while RelationMatchProfile.objects.filter(share_token=share_token).exists():
        share_token = make_share_token()

    return RelationMatchProfile.objects.create(
        participant_type=context.participant_type,
        user=context.user,
        participant_name=context.participant_name,
        visitor_token_hash=context.visitor_token_hash,
        test=test,
        dimension_scores=dimension_scores,
        summary_text=build_profile_summary(context.participant_name, dimension_scores),
        share_code=share_code,
        share_token=share_token,
    )


def select_relation_type(profile_a: RelationMatchProfile, profile_b: RelationMatchProfile) -> str:
    scores_a = cast(dict[str, Any], cast(Any, profile_a).dimension_scores)
    scores_b = cast(dict[str, Any], cast(Any, profile_b).dimension_scores)
    gaps = {dimension: abs(int(scores_a[dimension]) - int(scores_b[dimension])) for dimension in DIMENSIONS}
    similarity = sum(10 - gap for gap in gaps.values()) / (len(DIMENSIONS) * 9)
    dominance_gap = gaps["dominance"] + gaps["maturity"]
    care_sum = int(scores_a["care"]) + int(scores_b["care"]) + int(scores_a["stability"]) + int(scores_b["stability"])
    play_sum = int(scores_a["playfulness"]) + int(scores_b["playfulness"])

    if similarity >= 0.9:
        return "twin" if play_sum >= 14 else "mirror"
    if dominance_gap >= 6 and play_sum >= 10:
        return "frienemy"
    if care_sum >= 28:
        return "harbor"
    if care_sum >= 24:
        return "companion"
    if gaps["empathy"] <= 2 and gaps["maturity"] <= 2:
        return "confidant"
    if gaps["romance"] >= 5 and play_sum <= 8:
        return "contrast"
    if gaps["dependence"] >= 4 and gaps["stability"] <= 2:
        return "complementary"
    if gaps["care"] <= 2 and gaps["playfulness"] <= 3 and play_sum >= 10:
        return "bestie"
    if gaps["dominance"] >= 4 and gaps["empathy"] <= 3:
        return "teacher_student"
    if gaps["stability"] <= 2 and gaps["maturity"] >= 5:
        return "growing"
    if gaps["playfulness"] >= 4:
        return "adventure"
    if gaps["dependence"] >= 5:
        return "healing"
    if dominance_gap <= 3 and gaps["care"] <= 3:
        return "siblings"
    if gaps["romance"] >= 4 and care_sum >= 20:
        return "parent_child"
    if gaps["dominance"] <= 2 and gaps["care"] <= 2:
        return "childhood_friend"
    return "bestie"


def build_pair_compare(profile_a: RelationMatchProfile, profile_b: RelationMatchProfile) -> dict[str, dict[str, int | str]]:
    compare: dict[str, dict[str, int | str]] = {}
    scores_a = cast(dict[str, Any], cast(Any, profile_a).dimension_scores)
    scores_b = cast(dict[str, Any], cast(Any, profile_b).dimension_scores)
    for dimension in DIMENSIONS:
        score_a = int(scores_a[dimension])
        score_b = int(scores_b[dimension])
        compare[dimension] = {
            "a": score_a,
            "b": score_b,
            "gap": abs(score_a - score_b),
            "shared": min(score_a, score_b),
            "tendency": "a" if score_a > score_b else "b" if score_b > score_a else "equal",
        }
    return compare


def build_pair_result_text(profile_a: RelationMatchProfile, profile_b: RelationMatchProfile, relation_type: str):
    relation_data = RELATION_TYPES[relation_type]
    compare = build_pair_compare(profile_a, profile_b)
    top_dimension_key = max(compare.items(), key=lambda item: item[1]["shared"])[0]
    top_dimension = dimension_label(top_dimension_key)
    participant_a = getattr(profile_a, "participant_name", "")
    participant_b = getattr(profile_b, "participant_name", "")
    summary_a = f"{participant_a} 更偏向在{top_dimension}和{relation_data['role_a']}上表现明显。"
    summary_b = f"{participant_b} 更偏向在{top_dimension}和{relation_data['role_b']}上表现明显。"
    explanation = (
        f"你们在{top_dimension}维度上的共同值较高，"
        f"这让 {participant_a} 和 {participant_b} 在相处时更容易形成 {relation_data['name']} 的感觉。"
    )
    return {
        "relation_type": relation_type,
        "subtitle": relation_data["subtitle"],
        "summary_a": summary_a,
        "summary_b": summary_b,
        "role_a": relation_data["role_a"],
        "role_b": relation_data["role_b"],
        "dimension_compare": compare,
        "relation_explain": explanation,
        "highlight_text": relation_data["highlight"],
        "advice_text": relation_data["advice"],
    }


def create_or_get_pair_result(profile_a: RelationMatchProfile, profile_b: RelationMatchProfile):
    profile_a_id = getattr(profile_a, "id", None)
    profile_b_id = getattr(profile_b, "id", None)
    if profile_a_id == profile_b_id:
        raise ValueError("不能和自己生成关系结果")

    first, second = sorted((profile_a, profile_b), key=lambda profile: getattr(profile, "id", 0))
    existing = RelationMatchPairResult.objects.filter(profile_a=first, profile_b=second).first()
    if existing:
        return existing, False

    relation_type = select_relation_type(first, second)
    payload = build_pair_result_text(first, second, relation_type)
    share_token = make_share_token()
    while RelationMatchPairResult.objects.filter(share_token=share_token).exists():
        share_token = make_share_token()

    result = RelationMatchPairResult.objects.create(
        profile_a=first,
        profile_b=second,
        share_token=share_token,
        **payload,
    )
    RelationMatchPairResultMember.objects.get_or_create(result=result, profile=first)
    RelationMatchPairResultMember.objects.get_or_create(result=result, profile=second)
    return result, True


def create_plugin_notifications(result: RelationMatchPairResult, trigger_profile: RelationMatchProfile):
    recipients = []
    profile_a_user_id = getattr(result.profile_a, "user_id", None)
    profile_b_user_id = getattr(result.profile_b, "user_id", None)
    if profile_a_user_id:
        recipients.append((getattr(result.profile_a, "user", None), result.profile_b))
    if profile_b_user_id:
        recipients.append((getattr(result.profile_b, "user", None), result.profile_a))
    for recipient, other_profile in recipients:
        if recipient is None:
            continue
        recipient_id = getattr(recipient, "id", None)
        trigger_user = getattr(trigger_profile, "user", None)
        other_name = getattr(other_profile, "participant_name", "")
        result_id = getattr(result, "id", None)
        notification_model: Any = Notification
        relation_type = str(getattr(result, "relation_type", ""))
        notification_model.objects.create(
            recipient=recipient,
            sender=trigger_user if getattr(trigger_profile, "user_id", None) else None,
            notification_type=Notification.Type.PLUGIN_EVENT,
            title="关系结果已生成",
            content=f"你和 {other_name} 的关系结果已生成：{RELATION_TYPES[relation_type]['name']}",
            link=f"/profile/{recipient_id}/plugins/relation-match/pairs/{result_id}/",
        )

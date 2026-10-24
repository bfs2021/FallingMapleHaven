import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.notifications.models import Notification
from apps.plugins.models import Plugin
from apps.plugins.relation_match.catalog import (
    DIMENSIONS,
    RELATION_TYPES,
    build_current_test_seed,
    build_dimension_max_raw_scores,
)
from apps.plugins.relation_match.models import (
    RelationMatchPairResult,
    RelationMatchProfile,
    RelationMatchQuestion,
    RelationMatchTest,
    RelationMatchTestAnswer,
    RelationMatchTestAnswerItem,
)
from apps.plugins.relation_match.services import (
    normalize_dimension_scores,
    score_answers,
    select_relation_type,
)


@pytest.fixture(autouse=True)
def _active_relation_match_plugin(db):
    Plugin.objects.update_or_create(
        plugin_type="relation_match",
        defaults={"name": "关系匹配", "is_active": True},
    )


# 匿名限流由根 conftest 的 _no_anon_throttle 全局关闭


def _url(name, *args):
    return reverse(f"relation-match-{name}", args=args)


def _current_test():
    return RelationMatchTest.objects.get(slug="current")


def _answer_payload(test, participant_name=None):
    answers = []
    for question in test.questions.order_by("order"):
        option = question.options.order_by("order").first()
        answers.append({"question_id": question.id, "selected_option_ids": [option.id]})
    payload = {"answers": answers}
    if participant_name is not None:
        payload["participant_name"] = participant_name
    return payload


class TestRelationMatchCatalog:
    def test_plugin_is_registered(self, alice_client):
        resp = alice_client.get(reverse("plugin-list"))
        assert resp.status_code == 200
        types = {item["type"] for item in resp.json()["data"]}
        assert "relation_match" in types

    def test_disabled_plugin_blocks_business_endpoints(self, alice_client):
        Plugin.objects.filter(plugin_type="relation_match").update(is_active=False)
        resp = alice_client.get(_url("current-test"))
        assert resp.status_code == 404
        assert resp.json()["code"] == 40004

    def test_current_test_has_exactly_40_questions_and_option_bounds(self, client):
        test = _current_test()
        assert test.status == RelationMatchTest.Status.PUBLISHED
        questions = list(test.questions.order_by("order"))
        assert len(questions) == 40
        for question in questions:
            option_count = question.options.count()
            assert 2 <= option_count <= 4

    def test_current_test_question_type_distribution(self, client):
        """Docs/18 §3 分布：24 单选 + 8 二选一 + 4 量表 + 4 多选。"""
        test = _current_test()
        counts = {}
        for question in test.questions.all():
            counts[question.question_type] = counts.get(question.question_type, 0) + 1
            if question.question_type == "either_or":
                assert question.options.count() == 2
            elif question.question_type == "multi_select":
                assert question.options.count() == 4
        assert counts == {
            "single_choice": 24,
            "either_or": 8,
            "scale": 4,
            "multi_select": 4,
        }

    def test_only_one_non_deleted_test_is_allowed(self):
        with pytest.raises(ValidationError):
            RelationMatchTest.objects.create(
                slug="another",
                title="另一套测试",
                status=RelationMatchTest.Status.DRAFT,
            )


def _scores(base=5, **overrides):
    scores = dict.fromkeys(DIMENSIONS, base)
    scores.update(overrides)
    return scores


def _profile_of(scores):
    return RelationMatchProfile(participant_name="校准", dimension_scores=scores)


# 16 类关系类型的可达性配对：每组画像对精心避开前置分支，命中目标类型（Docs/18 §6.2）。
_REACHABLE_PAIRS = {
    "twin": (_scores(10), _scores(10)),
    "mirror": (_scores(1), _scores(1)),
    "frienemy": (
        _scores(dominance=10, maturity=10, playfulness=8),
        _scores(dominance=1, maturity=1, playfulness=8),
    ),
    "harbor": (
        _scores(dominance=1, care=10, romance=1, playfulness=1, stability=10),
        _scores(dominance=9, care=10, romance=9, playfulness=8, stability=10),
    ),
    "companion": (
        _scores(care=7, stability=6, dominance=1, romance=1, playfulness=1),
        _scores(care=7, stability=6, dominance=9, romance=9, playfulness=8),
    ),
    "confidant": (
        _scores(dominance=1, care=1, dependence=1, romance=1, playfulness=1),
        _scores(dominance=10, dependence=10, romance=10, playfulness=8),
    ),
    "contrast": (_scores(2, romance=10), _scores(8, romance=1, playfulness=6)),
    "complementary": (
        _scores(dependence=10, empathy=3),
        _scores(dependence=5, empathy=7, dominance=9, romance=9, playfulness=9),
    ),
    "bestie": (
        _scores(dominance=2, care=6, dependence=6, empathy=3, romance=5, playfulness=7, stability=1, maturity=6),
        _scores(dominance=6, care=6, dependence=6, empathy=9, romance=9, playfulness=8, stability=5, maturity=6),
    ),
    "teacher_student": (
        _scores(dominance=10, care=9, empathy=5, playfulness=2, maturity=2),
        _scores(dominance=2, care=3, empathy=8, playfulness=7, maturity=5),
    ),
    "growing": (
        _scores(maturity=10, playfulness=2, romance=2),
        _scores(maturity=2, playfulness=7, romance=9),
    ),
    "adventure": (
        _scores(empathy=8, romance=9, playfulness=10, stability=8),
        _scores(empathy=4, romance=2, playfulness=3, stability=2),
    ),
    "healing": (
        _scores(care=8, dependence=10, empathy=8, romance=2, playfulness=5, stability=7),
        _scores(care=4, dependence=2, empathy=4, romance=9, playfulness=7, stability=3),
    ),
    "siblings": (
        _scores(care=8, empathy=8, romance=10, playfulness=6, stability=5),
        _scores(care=5, empathy=4, romance=1, playfulness=4, stability=2),
    ),
    "parent_child": (
        _scores(dominance=9, care=6, empathy=2, romance=2, playfulness=3, stability=3),
        _scores(dominance=3, care=9, empathy=8, romance=9, playfulness=6, stability=3),
    ),
    "childhood_friend": (
        _scores(dominance=6, care=5, dependence=8, empathy=2, romance=1, playfulness=3, stability=3, maturity=8),
        _scores(dominance=5, care=6, dependence=5, empathy=5, romance=4, playfulness=5, stability=6, maturity=5),
    ),
}


class TestRelationMatchCalibration:
    """Docs/18 §6 校准：种子内容、极端画像 9-10、中性画像 4-6、16 类关系类型全覆盖。"""

    def test_seeded_questions_match_catalog(self, client):
        test = _current_test()
        seeds = build_current_test_seed()
        questions = list(test.questions.order_by("order"))
        assert len(questions) == len(seeds) == 40
        for question, seed in zip(questions, seeds):
            assert question.question_text == seed.question_text
            assert question.question_type == seed.question_type
            assert question.scene_tag == seed.scene_tag
            assert list(question.options.order_by("order").values_list("option_text", flat=True)) == list(seed.option_texts)

    def test_seed_weights_follow_docs18_convention(self):
        for seed in build_current_test_seed():
            if seed.question_type == "scale":
                assert seed.option_texts == ("完全符合", "比较符合", "不太符合", "完全不符合")
                dimension = next(iter(seed.option_payloads[0]))
                assert [payload.get(dimension, 0) for payload in seed.option_payloads] == [3, 2, 1, 0]
                continue
            for payload in seed.option_payloads:
                assert len(payload) <= 1
                assert all(weight == 3 for weight in payload.values())

    @pytest.mark.parametrize("dimension", DIMENSIONS)
    def test_extreme_answers_score_9_or_10_on_target_dimension(self, client, dimension):
        test = _current_test()
        answer_map = {}
        for question in test.questions.prefetch_related("options").order_by("order"):
            options = list(question.options.order_by("order"))
            if question.question_type == "multi_select":
                selected = [option.id for option in options if option.dimension_payload.get(dimension, 0) > 0]
                answer_map[question.id] = selected or [options[0].id]
            else:
                answer_map[question.id] = [max(options, key=lambda option: option.dimension_payload.get(dimension, 0)).id]
        scores, _items = score_answers(test, answer_map)
        assert 9 <= scores[dimension] <= 10

    def test_half_max_raw_scores_fall_in_mid_band(self):
        raw_scores = {dimension: value // 2 for dimension, value in build_dimension_max_raw_scores().items()}
        scores = normalize_dimension_scores(raw_scores)
        assert all(4 <= score <= 6 for score in scores.values())

    @pytest.mark.parametrize("relation_type", sorted(RELATION_TYPES))
    def test_all_relation_types_are_reachable(self, relation_type):
        scores_a, scores_b = _REACHABLE_PAIRS[relation_type]
        assert select_relation_type(_profile_of(scores_a), _profile_of(scores_b)) == relation_type


class TestRelationMatchPublicTest:
    def test_public_current_test_does_not_expose_private_fields_and_sets_cookie(self, client):
        resp = client.get(_url("current-test"))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["questions"]) == 40
        first_question = data["questions"][0]
        assert "dimension_payload" not in first_question
        assert "correct_option" not in first_question
        assert resp.cookies.get("fmh_relation_visitor_id") is not None
        assert resp.cookies["fmh_relation_visitor_id"]["max-age"] == 60 * 60 * 24 * 365

    def test_malformed_answers_return_parameter_error(self, client):
        client.get(_url("current-test"))
        malformed_answers = [None] * 40
        resp = client.post(
            _url("current-submission"),
            {"participant_name": "秋风", "answers": malformed_answers},
            format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 40001


class TestRelationMatchVisitorFlow:
    def test_visitor_submit_creates_profile_and_hashes_cookie(self, client):
        test = _current_test()
        client.get(_url("current-test"))
        resp = client.post(_url("current-submission"), _answer_payload(test, participant_name="秋风"), format="json")
        assert resp.status_code == 201
        submission_id = RelationMatchTestAnswer.objects.latest("id").id
        answer = RelationMatchTestAnswer.objects.get(pk=submission_id)
        profile = RelationMatchProfile.objects.get(visitor_token_hash=answer.visitor_token_hash)
        assert profile.participant_name == "秋风"
        assert profile.visitor_token_hash != client.cookies["fmh_relation_visitor_id"].value
        assert RelationMatchTestAnswerItem.objects.filter(answer=answer).count() == 40
        assert resp.json()["data"]["next_action"] == "invite"
        assert resp.json()["data"]["result_url"] is None

    def test_visitor_share_url_points_to_join_route(self, client):
        """访客画像 share_url 必须指向独立落地路由，严禁回退到画像自身 id。"""
        test = _current_test()
        client.get(_url("current-test"))
        resp = client.post(_url("current-submission"), _answer_payload(test, participant_name="秋风"), format="json")
        assert resp.status_code == 201
        data = resp.json()["data"]
        share_url = data["share_url"]
        assert share_url.startswith("/plugins/relation-match/join?shareCode=")
        assert f"/profile/{data['profile']['id']}/" not in share_url

    def test_logged_in_share_url_points_to_profile_route(self, alice_client, alice):
        """登录用户画像 share_url 指向自己的插件主页。"""
        test = _current_test()
        resp = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        assert resp.status_code == 201
        share_url = resp.json()["data"]["share_url"]
        assert share_url == f"/profile/{alice.id}/plugins/relation-match?shareCode={resp.json()['data']['share_code']}"

    def test_visitor_submit_with_share_code_auto_matches(self, client, alice_client, alice):
        """访客从分享链接答题，提交携带 share_code，答完自动匹配并返回 result_url。"""
        test = _current_test()
        alice_submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        assert alice_submit.status_code == 201
        share_code = alice_submit.json()["data"]["share_code"]

        client.get(_url("current-test"))
        payload = _answer_payload(test, participant_name="小明")
        payload["share_code"] = share_code
        resp = client.post(_url("current-submission"), payload, format="json")
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["next_action"] == "match"
        assert data["result_url"].startswith("/plugins/relation-match/pairs/")
        assert data["pair"]["id"]
        assert RelationMatchPairResult.objects.count() == 1
        # 访客生成结果不通知（recipient 为访客的用户不存在，登录方 Alice 收到通知）
        assert Notification.objects.filter(notification_type=Notification.Type.PLUGIN_EVENT).count() == 1

    def test_visitor_duplicate_submit_is_rejected(self, client):
        test = _current_test()
        client.get(_url("current-test"))
        payload = _answer_payload(test, participant_name="秋风")
        first = client.post(_url("current-submission"), payload, format="json")
        assert first.status_code == 201
        second = client.post(_url("current-submission"), payload, format="json")
        assert second.status_code == 400
        assert second.json()["code"] == 40005

    def test_logged_in_duplicate_submit_is_rejected(self, alice_client):
        test = _current_test()
        payload = _answer_payload(test)
        first = alice_client.post(_url("current-submission"), payload, format="json")
        second = alice_client.post(_url("current-submission"), payload, format="json")
        assert first.status_code == 201
        assert second.status_code == 400
        assert second.json()["code"] == 40005

    def test_visitor_history_returns_empty_and_sets_cookie(self, client):
        resp = client.get(_url("my-pairs"))
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["total"] == 0
        assert body["results"] == []
        assert resp.cookies.get("fmh_relation_visitor_id") is not None

    def test_multi_select_single_choice_is_stored_as_array(self, client):
        test = _current_test()
        question = test.questions.order_by("order").first()
        question.question_type = RelationMatchQuestion.Type.MULTI_SELECT
        question.save(update_fields=["question_type"])

        client.get(_url("current-test"))
        resp = client.post(_url("current-submission"), _answer_payload(test, participant_name="秋风"), format="json")
        assert resp.status_code == 201

        answer = RelationMatchTestAnswer.objects.latest("id")
        item = RelationMatchTestAnswerItem.objects.get(answer=answer, question=question)
        assert item.selected_options == [question.options.order_by("order").first().id]


class TestRelationMatchPairing:
    def test_logged_in_match_creates_idempotent_pair_and_notifications(self, alice_client, bob_client, alice, bob):
        test = _current_test()
        alice_submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        bob_submit = bob_client.post(_url("current-submission"), _answer_payload(test), format="json")
        assert alice_submit.status_code == 201
        assert bob_submit.status_code == 201

        alice_share_code = alice_submit.json()["data"]["share_code"]
        first_match = bob_client.post(_url("share-match", alice_share_code), {}, format="json")
        assert first_match.status_code == 200
        pair_id = first_match.json()["data"]["id"]
        assert first_match.json()["data"]["relation_type_name"]

        second_match = bob_client.post(_url("share-match", alice_share_code), {}, format="json")
        assert second_match.status_code == 200
        assert second_match.json()["data"]["id"] == pair_id

        assert Notification.objects.filter(notification_type=Notification.Type.PLUGIN_EVENT).count() == 2
        assert RelationMatchPairResult.objects.count() == 1

    def test_self_match_is_rejected(self, alice_client, alice):
        test = _current_test()
        submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        assert submit.status_code == 201
        share_code = submit.json()["data"]["share_code"]
        resp = alice_client.post(_url("share-match", share_code), {}, format="json")
        assert resp.status_code == 400
        assert resp.json()["code"] == 40005

    def test_public_pair_detail_hides_private_tokens(self, alice_client, bob_client):
        test = _current_test()
        alice_submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        bob_client.post(_url("current-submission"), _answer_payload(test), format="json")
        share_code = alice_submit.json()["data"]["share_code"]
        match = bob_client.post(_url("share-match", share_code), {}, format="json")
        result_id = match.json()["data"]["id"]

        client = alice_client
        resp = client.get(_url("pair-detail", result_id))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "share_token" not in data
        assert "access_token_hash" not in data
        assert "dimension_payload" not in data

    def test_logged_in_history_lists_pair_once(self, alice_client, bob_client):
        test = _current_test()
        alice_submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        bob_client.post(_url("current-submission"), _answer_payload(test), format="json")
        share_code = alice_submit.json()["data"]["share_code"]
        bob_client.post(_url("share-match", share_code), {}, format="json")

        resp = alice_client.get(_url("my-pairs"))
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["total"] == 1
        assert body["results"][0]["pair_id"]


class TestRelationMatchHome:
    def test_home_includes_share_info_and_history_for_owner(self, alice_client, alice):
        test = _current_test()
        submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        assert submit.status_code == 201
        resp = alice_client.get(_url("home", alice.id))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["has_profile"] is True
        assert data["share_code"]
        assert data["history"]["total"] == 0
        # 有画像但尚未配对：下一步应为“邀请中”
        assert data["next_action"] == "invite"

    def test_home_next_action_becomes_match_after_pairing(self, alice_client, bob_client, alice):
        test = _current_test()
        alice_submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        bob_client.post(_url("current-submission"), _answer_payload(test), format="json")
        share_code = alice_submit.json()["data"]["share_code"]
        bob_client.post(_url("share-match", share_code), {}, format="json")

        resp = alice_client.get(_url("home", alice.id))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["history"]["total"] == 1
        assert data["next_action"] == "match"


class TestRelationMatchProfileCard:
    def test_profile_card_includes_entry_text_and_share_code(self, alice_client, alice):
        # 未完成测试：has_profile=False、share_code=None，但入口文案必须存在
        resp = alice_client.get(reverse("profile-plugin-cards", args=[alice.id]))
        assert resp.status_code == 200
        card = next(item for item in resp.json()["data"] if item["type"] == "relation_match")
        assert card["data"]["entry_text"] == "看看你们像什么"
        assert card["data"]["has_profile"] is False
        assert card["data"]["share_code"] is None

        # 完成测试后：画像已生成，share_code 必须返回，入口卡才能显示短码
        test = _current_test()
        submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        assert submit.status_code == 201
        resp = alice_client.get(reverse("profile-plugin-cards", args=[alice.id]))
        card = next(item for item in resp.json()["data"] if item["type"] == "relation_match")
        assert card["data"]["entry_text"] == "看看你们像什么"
        assert card["data"]["has_profile"] is True
        assert card["data"]["share_code"]


class TestRelationMatchAdminHooks:
    def test_admin_hooks_expose_profiles_tests_pairs_and_stats(self, admin_client, alice_client, bob_client):
        test = _current_test()
        alice_submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        bob_client.post(_url("current-submission"), _answer_payload(test), format="json")
        bob_client.post(_url("share-match", alice_submit.json()["data"]["share_code"]), {}, format="json")

        tests_resp = admin_client.get(reverse("admin-relation-match-tests"))
        submissions_resp = admin_client.get(reverse("admin-relation-match-submissions"))
        profiles_resp = admin_client.get(reverse("admin-relation-match-profiles"))
        pairs_resp = admin_client.get(reverse("admin-relation-match-pairs"))
        stats_resp = admin_client.get(reverse("admin-relation-match-stats"))

        assert tests_resp.status_code == 200
        assert submissions_resp.status_code == 200
        assert profiles_resp.status_code == 200
        assert pairs_resp.status_code == 200
        assert stats_resp.status_code == 200
        assert tests_resp.json()["data"]["total"] >= 1
        assert submissions_resp.json()["data"]["total"] >= 2
        assert profiles_resp.json()["data"]["total"] >= 2
        assert pairs_resp.json()["data"]["total"] >= 1
        assert stats_resp.json()["data"]["total_pairs"] >= 1

    def test_admin_submission_detail_includes_option_texts(self, admin_client, alice_client):
        test = _current_test()
        submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        assert submit.status_code == 201
        submission = RelationMatchTestAnswer.objects.latest("id")
        resp = admin_client.get(reverse("admin-relation-match-submission-detail", args=[submission.id]))
        assert resp.status_code == 200
        data = resp.json()["data"]
        answers = data["answers"]
        assert len(answers) == 40
        first = answers[0]
        assert first["question_text"]
        assert first["question_type"]
        assert first["selected_option_texts"]
        assert first["selected_option_texts"][0]


class TestRelationMatchMyPage:
    def test_visitor_my_returns_empty_state_and_sets_cookie(self, client):
        """访客未答题时 my/ 返回 has_profile=False、share_code/share_url 为 null。"""
        resp = client.get(_url("my"))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["has_profile"] is False
        assert data["profile"] is None
        assert data["share_code"] is None
        assert data["share_url"] is None
        assert data["history"]["results"] == []
        assert resp.cookies.get("fmh_relation_visitor_id") is not None

    def test_visitor_my_returns_state_and_history_after_match(self, client, alice_client):
        """访客答完并参与匹配后，my/ 返回其画像状态与匹配历史。"""
        test = _current_test()
        alice_submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        share_code = alice_submit.json()["data"]["share_code"]

        client.get(_url("current-test"))
        payload = _answer_payload(test, participant_name="小明")
        payload["share_code"] = share_code
        client.post(_url("current-submission"), payload, format="json")

        resp = client.get(_url("my"))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["has_profile"] is True
        assert data["share_code"]
        assert data["share_url"].startswith("/plugins/relation-match/join?shareCode=")
        assert data["history"]["total"] == 1
        assert data["history"]["results"][0]["result_url"].startswith("/plugins/relation-match/pairs/")
        assert data["next_action"] == "match"

    def test_logged_in_my_returns_own_state(self, alice_client, alice):
        test = _current_test()
        submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        assert submit.status_code == 201
        resp = alice_client.get(_url("my"))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["has_profile"] is True
        assert data["share_url"] == f"/profile/{alice.id}/plugins/relation-match?shareCode={data['share_code']}"

    def test_visitor_my_pairs_after_match(self, client, alice_client):
        """访客按 Cookie 哈希可查看自己的匹配历史（允许未登录）。"""
        test = _current_test()
        alice_submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        share_code = alice_submit.json()["data"]["share_code"]

        client.get(_url("current-test"))
        payload = _answer_payload(test, participant_name="小明")
        payload["share_code"] = share_code
        client.post(_url("current-submission"), payload, format="json")

        resp = client.get(_url("my-pairs"))
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["total"] == 1
        assert body["results"][0]["result_url"].startswith("/plugins/relation-match/pairs/")


class TestRelationMatchShareDetail:
    def test_share_detail_returns_profile_summary(self, alice_client):
        test = _current_test()
        submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        share_code = submit.json()["data"]["share_code"]
        resp = alice_client.get(_url("share-detail", share_code))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["share_code"] == share_code
        assert data["participant_name"]

    def test_share_detail_unknown_code_returns_404(self, client):
        resp = client.get(_url("share-detail", "000000"))
        assert resp.status_code == 404
        assert resp.json()["code"] == 40004

    def test_visitor_share_detail_returns_join_route_url(self, client, alice_client):
        """访客画像的 share_url 通过落地接口返回时必须指向独立落地路由。"""
        test = _current_test()
        client.get(_url("current-test"))
        submit = client.post(_url("current-submission"), _answer_payload(test, participant_name="秋风"), format="json")
        share_code = submit.json()["data"]["share_code"]

        resp = client.get(_url("share-detail", share_code))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["share_url"].startswith("/plugins/relation-match/join?shareCode=")


class TestRelationMatchResultLink:
    def test_pair_result_share_url_is_independent_route(self, alice_client, bob_client):
        """结果 share_url 必须为独立路由 /plugins/relation-match/pairs/{id}/。"""
        test = _current_test()
        alice_submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        bob_client.post(_url("current-submission"), _answer_payload(test), format="json")
        share_code = alice_submit.json()["data"]["share_code"]
        match = bob_client.post(_url("share-match", share_code), {}, format="json")
        result_id = match.json()["data"]["id"]

        detail = bob_client.get(_url("pair-detail", result_id))
        assert detail.status_code == 200
        assert detail.json()["data"]["share_url"] == f"/plugins/relation-match/pairs/{result_id}/"

    def test_pair_detail_accessible_without_login(self, client, alice_client, bob_client):
        """结果链接即授权：未登录也可打开独立路由结果页。"""
        test = _current_test()
        alice_submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        bob_client.post(_url("current-submission"), _answer_payload(test), format="json")
        share_code = alice_submit.json()["data"]["share_code"]
        match = bob_client.post(_url("share-match", share_code), {}, format="json")
        result_id = match.json()["data"]["id"]

        resp = client.get(_url("pair-detail", result_id))
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == result_id


class TestRelationMatchLocalizedText:
    DIMENSION_KEYS = [
        "dominance", "care", "dependence", "empathy",
        "romance", "playfulness", "stability", "maturity",
    ]
    DIMENSION_LABELS = ["主导", "照顾", "依赖", "共情", "浪漫", "玩乐", "稳定", "成熟"]

    def test_profile_summary_uses_chinese_dimension_names(self, alice_client, alice):
        test = _current_test()
        resp = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        assert resp.status_code == 201
        profile = RelationMatchProfile.objects.get(user=alice, test=test)
        summary = profile.summary_text
        for key in self.DIMENSION_KEYS:
            assert key not in summary
        assert any(label in summary for label in self.DIMENSION_LABELS)

    def test_pair_result_text_uses_chinese_dimension_names(self, alice_client, bob_client):
        test = _current_test()
        alice_submit = alice_client.post(_url("current-submission"), _answer_payload(test), format="json")
        bob_client.post(_url("current-submission"), _answer_payload(test), format="json")
        share_code = alice_submit.json()["data"]["share_code"]
        match = bob_client.post(_url("share-match", share_code), {}, format="json")
        assert match.status_code == 200
        data = match.json()["data"]
        for field in ("summary_a", "summary_b", "relation_explain"):
            for key in self.DIMENSION_KEYS:
                assert key not in data[field]
        assert any(label in data["summary_a"] or label in data["summary_b"] for label in self.DIMENSION_LABELS)

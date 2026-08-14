import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.notifications.models import Notification
from apps.plugins.models import Plugin
from apps.plugins.relation_match.models import (
    RelationMatchPairResult,
    RelationMatchProfile,
    RelationMatchQuestion,
    RelationMatchTest,
    RelationMatchTestAnswer,
    RelationMatchTestAnswerItem,
)


@pytest.fixture(autouse=True)
def _active_relation_match_plugin(db):
    Plugin.objects.update_or_create(
        plugin_type="relation_match",
        defaults={"name": "关系匹配", "is_active": True},
    )


@pytest.fixture(autouse=True)
def _no_anon_throttle(settings):
    """访客流程会产生大量匿名请求，禁用 AnonRateThrottle 避免 429（与 test_accounts.py 保持一致）"""
    from django.core.cache import cache

    cache.clear()
    current = dict(settings.REST_FRAMEWORK)
    rates = dict(current.get("DEFAULT_THROTTLE_RATES", {}))
    rates["anon"] = None  # Disable anon throttling
    current["DEFAULT_THROTTLE_RATES"] = rates
    settings.REST_FRAMEWORK = current
    from rest_framework.settings import api_settings

    api_settings._cached_attrs.discard("DEFAULT_THROTTLE_RATES")
    api_settings.__dict__.pop("DEFAULT_THROTTLE_RATES", None)
    api_settings.__dict__.pop("_user_settings", None)


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

    def test_only_one_non_deleted_test_is_allowed(self):
        with pytest.raises(ValidationError):
            RelationMatchTest.objects.create(
                slug="another",
                title="另一套测试",
                status=RelationMatchTest.Status.DRAFT,
            )


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

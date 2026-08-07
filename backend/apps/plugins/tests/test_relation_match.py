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

    def test_visitor_duplicate_submit_is_rejected(self, client):
        test = _current_test()
        client.get(_url("current-test"))
        payload = _answer_payload(test, participant_name="秋风")
        first = client.post(_url("current-submission"), payload, format="json")
        assert first.status_code == 201
        second = client.post(_url("current-submission"), payload, format="json")
        assert second.status_code == 400
        assert second.json()["code"] == 40005

    def test_visitor_history_requires_login(self, client):
        resp = client.get(_url("my-pairs"))
        assert resp.status_code == 403


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

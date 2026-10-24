import pytest
from rest_framework import status

from apps.plugins.models import Plugin

QUIZ = "/api/v1/plugins/quiz/"
QUESTION_BOX = "/api/v1/plugins/question-box/"
SUMMARY = "/api/v1/plugins/summary/"

pytestmark = pytest.mark.django_db


def _unwrap(resp):
    return resp.data.get("data", resp.data)


@pytest.fixture(autouse=True)
def _active_plugins():
    Plugin.objects.update_or_create(plugin_type="quiz", defaults={"name": "默契问答", "is_active": True})
    Plugin.objects.update_or_create(plugin_type="question_box", defaults={"name": "匿名提问箱", "is_active": True})


def _quiz_question(index, correct_order=1):
    return {
        "question_text": f"Question {index}?",
        "order": index,
        "correct_option_order": correct_order,
        "options": [
            {"option_text": f"A{index}", "order": 1},
            {"option_text": f"B{index}", "order": 2},
        ],
    }


def _quiz_payload(title="Acceptance quiz", count=10):
    return {
        "title": title,
        "questions": [_quiz_question(index) for index in range(1, count + 1)],
    }


def _create_published_test(client):
    resp = client.post(QUIZ + "my/tests/", _quiz_payload(), format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    test_id = _unwrap(resp)["id"]
    resp = client.post(QUIZ + f"my/tests/{test_id}/publish/", format="json")
    assert resp.status_code == status.HTTP_200_OK
    return _unwrap(resp)


def _answer_payload(test, correct=True):
    answers = []
    for question in test["questions"]:
        selected = question["options"][0 if correct else 1]
        answers.append({"question_id": question["id"], "selected_option_id": selected["id"]})
    return {"answers": answers}


class TestQuizOwnerTests:
    """Owner manages /plugins/quiz/my/tests/."""

    def test_create_draft(self, alice_client):
        resp = alice_client.post(QUIZ + "my/tests/", _quiz_payload(count=2), format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = _unwrap(resp)
        assert data["status"] == "draft"
        assert data["question_count"] == 2

    def test_create_requires_auth(self, client):
        resp = client.post(QUIZ + "my/tests/", _quiz_payload(count=2), format="json")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_publish_requires_ten_questions(self, alice_client):
        resp = alice_client.post(QUIZ + "my/tests/", _quiz_payload(count=2), format="json")
        test_id = _unwrap(resp)["id"]
        resp = alice_client.post(QUIZ + f"my/tests/{test_id}/publish/", format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001

    def test_publish_success(self, alice_client):
        data = _create_published_test(alice_client)
        assert data["status"] == "published"
        assert data["question_count"] == 10


class TestQuizPublicFlow:
    """Public homepage quiz flow."""

    def test_public_list_and_detail_allow_anonymous(self, client, alice_client, alice):
        test = _create_published_test(alice_client)

        resp = client.get(QUIZ + f"users/{alice.id}/tests/")
        assert resp.status_code == status.HTTP_200_OK
        assert _unwrap(resp)["results"][0]["id"] == test["id"]

        resp = client.get(QUIZ + f"tests/{test['id']}/")
        assert resp.status_code == status.HTTP_200_OK
        question = _unwrap(resp)["questions"][0]
        assert "correct_option_id" not in question
        assert resp.cookies.get("fmh_visitor_id") is not None

    def test_logged_in_submit_redirects_to_leaderboard(self, alice_client, bob_client):
        test = _create_published_test(alice_client)
        detail = _unwrap(bob_client.get(QUIZ + f"tests/{test['id']}/"))

        resp = bob_client.post(QUIZ + f"tests/{test['id']}/submissions/", _answer_payload(detail), format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        data = _unwrap(resp)
        assert data["submission"]["correct_count"] == 10
        assert "leaderboard" in data["leaderboard_url"]

    def test_visitor_submit_sets_cookie(self, client, alice_client):
        test = _create_published_test(alice_client)
        detail_resp = client.get(QUIZ + f"tests/{test['id']}/")
        detail = _unwrap(detail_resp)
        payload = _answer_payload(detail, correct=False)
        payload["participant_name"] = "Visitor"

        resp = client.post(QUIZ + f"tests/{test['id']}/submissions/", payload, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.cookies.get("fmh_visitor_id") is not None or detail_resp.cookies.get("fmh_visitor_id") is not None

    def test_duplicate_submit_rejected(self, alice_client, bob_client):
        test = _create_published_test(alice_client)
        detail = _unwrap(bob_client.get(QUIZ + f"tests/{test['id']}/"))
        payload = _answer_payload(detail)
        bob_client.post(QUIZ + f"tests/{test['id']}/submissions/", payload, format="json")

        resp = bob_client.post(QUIZ + f"tests/{test['id']}/submissions/", payload, format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40005

    def test_owner_cannot_submit_own_test(self, alice_client):
        test = _create_published_test(alice_client)
        detail = _unwrap(alice_client.get(QUIZ + f"tests/{test['id']}/"))

        resp = alice_client.post(QUIZ + f"tests/{test['id']}/submissions/", _answer_payload(detail), format="json")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40005


class TestQuizLeaderboard:
    """GET /plugins/quiz/tests/{id}/leaderboard/."""

    def test_leaderboard_success(self, alice_client, bob_client):
        test = _create_published_test(alice_client)
        detail = _unwrap(bob_client.get(QUIZ + f"tests/{test['id']}/"))
        submit = bob_client.post(QUIZ + f"tests/{test['id']}/submissions/", _answer_payload(detail), format="json")

        resp = bob_client.get(QUIZ + f"tests/{test['id']}/leaderboard/", {"answerId": _unwrap(submit)["submission"]["id"]})

        assert resp.status_code == status.HTTP_200_OK
        data = _unwrap(resp)
        assert data["leaderboard"]["total"] == 1
        assert data["leaderboard"]["results"][0]["rank"] == 1
        assert data["leaderboard"]["results"][0]["is_current"] is True

    def test_leaderboard_empty_for_no_submissions(self, client, alice_client):
        test = _create_published_test(alice_client)
        resp = client.get(QUIZ + f"tests/{test['id']}/leaderboard/")
        assert resp.status_code == status.HTTP_200_OK
        assert _unwrap(resp)["leaderboard"]["total"] == 0


class TestQuestionBoxAsk:
    """POST /plugins/question-box/ — PRD §2.7"""

    def test_ask_anonymous_question(self, charlie_client, bob):
        resp = charlie_client.post(QUESTION_BOX, {
            "recipient_id": bob.id, "content": "What is your secret?",
        })
        assert resp.status_code == status.HTTP_201_CREATED

    def test_ask_public_question(self, charlie_client, bob):
        resp = charlie_client.post(QUESTION_BOX, {
            "recipient_id": bob.id, "content": "Public question?", "is_public": True,
        })
        assert resp.status_code == status.HTTP_201_CREATED

    def test_requires_auth(self, client, bob):
        resp = client.post(QUESTION_BOX, {
            "recipient_id": bob.id, "content": "Hack?",
        })
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestQuestionBoxInbox:
    """GET /plugins/question-box/inbox/ — PRD §2.7"""

    def test_view_inbox(self, charlie_client, bob_client, bob):
        charlie_client.post(QUESTION_BOX, {
            "recipient_id": bob.id, "content": "Anonymous Q?",
        })
        resp = bob_client.get(QUESTION_BOX + "inbox/")
        assert resp.status_code == status.HTTP_200_OK
        items = _unwrap(resp)
        if isinstance(items, dict):
            items = items.get("results", [])
        assert len(items) >= 1
        assert any("Anonymous Q?" in str(i.get("content", "")) for i in items)

    def test_requires_auth(self, client):
        resp = client.get(QUESTION_BOX + "inbox/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestQuestionBoxAnswer:
    """POST /plugins/question-box/{id}/answer/ — PRD §2.7"""

    def test_answer_question(self, charlie_client, bob_client, bob):
        resp = charlie_client.post(QUESTION_BOX, {
            "recipient_id": bob.id, "content": "Your thought?",
        })
        q_id = _unwrap(resp).get("id") or resp.data.get("data", {}).get("id")
        assert q_id is not None
        resp = bob_client.post(QUESTION_BOX + f"{q_id}/answer/", {"answer": "My answer"})
        assert resp.status_code == status.HTTP_200_OK

    def test_requires_auth(self, charlie_client, bob_client, bob, client):
        resp = charlie_client.post(QUESTION_BOX, {
            "recipient_id": bob.id, "content": "Your thought?",
        })
        q_id = _unwrap(resp).get("id") or resp.data.get("data", {}).get("id")
        resp = client.post(QUESTION_BOX + f"{q_id}/answer/", {"answer": "Answer"})
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestQuestionBoxDelete:
    """DELETE /plugins/question-box/{id}/delete/ — PRD §2.7"""

    def test_delete_inbox_question_as_recipient(self, charlie_client, bob_client, bob):
        charlie_client.post(QUESTION_BOX, {
            "recipient_id": bob.id, "content": "To delete",
        })
        inbox = _unwrap(bob_client.get(QUESTION_BOX + "inbox/"))
        q_id = None
        if isinstance(inbox, dict):
            for q in inbox.get("results", []):
                if q["content"] == "To delete":
                    q_id = q["id"]
                    break
        assert q_id is not None
        resp = bob_client.delete(QUESTION_BOX + f"{q_id}/delete/")
        assert resp.status_code == status.HTTP_200_OK

    def test_requires_auth(self, charlie_client, bob, client):
        resp = charlie_client.post(QUESTION_BOX, {
            "recipient_id": bob.id, "content": "To delete",
        })
        q_id_1 = _unwrap(resp).get("id")
        assert q_id_1 is not None
        resp = client.delete(QUESTION_BOX + f"{q_id_1}/delete/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestPluginSummary:
    """GET /plugins/summary/ — PRD §2.7"""

    def test_summary_returns_all_active_plugins(self, alice_client):
        resp = alice_client.get(SUMMARY)
        assert resp.status_code == status.HTTP_200_OK
        items = _unwrap(resp)
        if isinstance(items, dict):
            items = items.get("results", [])
        assert len(items) >= 2
        types = {i["type"] for i in items}
        assert "quiz" in types
        assert "question_box" in types

    def test_summary_item_has_expected_fields(self, alice_client):
        items = _unwrap(alice_client.get(SUMMARY))
        if isinstance(items, dict):
            items = items.get("results", [])
        for item in items:
            for field in ("type", "name", "icon", "description", "data", "is_active", "route"):
                assert field in item

    def test_requires_auth(self, client):
        resp = client.get(SUMMARY)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestAuthRequired:
    @pytest.mark.parametrize("method,url,body", [
        ("post", QUIZ + "my/tests/", _quiz_payload(count=2)),
        ("get", QUIZ + "my/tests/", None),
        ("get", QUIZ + "my/submissions/", None),
        ("post", QUESTION_BOX, {"recipient_id": 1, "content": "test"}),
        ("get", QUESTION_BOX + "inbox/", None),
        ("get", SUMMARY, None),
    ])
    def test_endpoint_requires_auth(self, client, method, url, body):
        fn = getattr(client, method)
        if body is not None:
            resp = fn(url, body, format="json")
        else:
            resp = fn(url)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

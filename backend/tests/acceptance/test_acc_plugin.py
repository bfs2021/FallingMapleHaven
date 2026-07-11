import pytest
from rest_framework import status

QUIZ = "/api/v1/plugins/quiz/"
QUESTION_BOX = "/api/v1/plugins/question-box/"
SUMMARY = "/api/v1/plugins/summary/"

pytestmark = pytest.mark.django_db


def _unwrap(resp):
    return resp.data.get("data", resp.data)


class TestQuizCreateQuestion:
    """POST /plugins/quiz/questions/ — PRD §2.7"""

    def test_create_question(self, alice_client, bob, friendship):
        resp = alice_client.post(QUIZ + "questions/", {
            "target_user_id": bob.id,
            "question": "What is my favorite color?",
            "correct_answer": "Blue",
        })
        assert resp.status_code == status.HTTP_201_CREATED

    def test_requires_auth(self, client, bob):
        resp = client.post(QUIZ + "questions/", {
            "target_user_id": bob.id, "question": "Q?", "correct_answer": "A",
        })
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestQuizReceivedQuestions:
    """GET /plugins/quiz/questions/received/ — PRD §2.7"""

    def test_get_received_questions(self, alice_client, bob_client, bob, friendship):
        alice_client.post(QUIZ + "questions/", {
            "target_user_id": bob.id, "question": "What is my favorite color?", "correct_answer": "Blue",
        })
        resp = bob_client.get(QUIZ + "questions/received/")
        assert resp.status_code == status.HTTP_200_OK
        data = _unwrap(resp)
        results = data.get("results", data if isinstance(data, list) else [])
        assert any(q["question"] == "What is my favorite color?" for q in results)

    def test_requires_auth(self, client):
        resp = client.get(QUIZ + "questions/received/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestQuizAnswerQuestion:
    """POST /plugins/quiz/questions/{id}/answer/ — PRD §2.7"""

    def _create_question(self, client, target, q="Favorite pet?", a="Dog"):
        resp = client.post(QUIZ + "questions/", {
            "target_user_id": target.id, "question": q, "correct_answer": a,
        })
        return _unwrap(resp).get("id") or resp.data.get("data", {}).get("id")

    def test_answer_correctly(self, alice_client, bob_client, bob, friendship):
        q_id = self._create_question(alice_client, bob)
        assert q_id is not None
        resp = bob_client.post(QUIZ + f"questions/{q_id}/answer/", {"answer": "Dog"})
        assert resp.status_code == status.HTTP_201_CREATED
        data = _unwrap(resp)
        assert data.get("is_correct") is True

    def test_answer_incorrectly(self, alice_client, bob_client, bob, friendship):
        q_id = self._create_question(alice_client, bob)
        assert q_id is not None
        resp = bob_client.post(QUIZ + f"questions/{q_id}/answer/", {"answer": "Cat"})
        assert resp.status_code == status.HTTP_201_CREATED
        data = _unwrap(resp)
        assert data.get("is_correct") is False
        assert data.get("correct_answer") == "Dog"

    def test_requires_auth(self, alice_client, bob_client, bob, friendship, client):
        q_id = self._create_question(alice_client, bob)
        resp = client.post(QUIZ + f"questions/{q_id}/answer/", {"answer": "A"})
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestQuizResult:
    """GET /plugins/quiz/result/{friend_id}/ — PRD §2.7"""

    def _create_question(self, client, target, q, a):
        client.post(QUIZ + "questions/", {
            "target_user_id": target.id, "question": q, "correct_answer": a,
        })

    def test_view_result(self, alice_client, bob_client, alice, bob, friendship):
        self._create_question(alice_client, bob, "Q1?", "A")
        self._create_question(alice_client, bob, "Q2?", "B")
        qs = _unwrap(bob_client.get(QUIZ + "questions/received/"))
        for q in qs.get("results", qs if isinstance(qs, list) else []):
            bob_client.post(QUIZ + f"questions/{q['id']}/answer/", {"answer": "A"})
        resp = bob_client.get(QUIZ + f"result/{alice.id}/")
        assert resp.status_code == status.HTTP_200_OK
        data = _unwrap(resp)
        assert "match_score" in data
        assert "total_questions" in data
        assert "correct_count" in data

    def test_requires_auth(self, client, alice):
        resp = client.get(QUIZ + f"result/{alice.id}/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestQuizLeaderboard:
    """GET /plugins/quiz/leaderboard/ — PRD §2.7"""

    def test_leaderboard_success(self, alice_client, bob_client, alice, bob, friendship):
        alice_client.post(QUIZ + "questions/", {
            "target_user_id": bob.id, "question": "Q?", "correct_answer": "A",
        })
        qs = _unwrap(bob_client.get(QUIZ + "questions/received/"))
        for q in qs.get("results", qs if isinstance(qs, list) else []):
            bob_client.post(QUIZ + f"questions/{q['id']}/answer/", {"answer": "A"})
        resp = bob_client.get(QUIZ + "leaderboard/")
        assert resp.status_code == status.HTTP_200_OK
        data = _unwrap(resp)
        assert "rankings" in data
        assert "avg_match_rate" in data
        assert "total_friends" in data

    def test_requires_auth(self, client):
        resp = client.get(QUIZ + "leaderboard/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_leaderboard_empty_for_no_questions(self, alice_client):
        resp = alice_client.get(QUIZ + "leaderboard/")
        assert resp.status_code == status.HTTP_200_OK


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
        ("post", QUIZ + "questions/", {"target_user_id": 1, "question": "Q", "correct_answer": "A"}),
        ("get", QUIZ + "questions/received/", None),
        ("get", QUIZ + "result/1/", None),
        ("get", QUIZ + "leaderboard/", None),
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

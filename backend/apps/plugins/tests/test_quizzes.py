import pytest
from django.urls import reverse
from apps.friends.models import Friendship
from apps.notifications.models import Notification
from apps.plugins.models import Plugin
from apps.plugins.quizzes.models import QuizQuestion, QuizAnswer, QuizResult


@pytest.fixture(autouse=True)
def _active_plugin(db):
    Plugin.objects.get_or_create(plugin_type="quiz", defaults={"name": "默契问答", "is_active": True})


def _url(name, *args):
    return reverse(f"quiz-{name}", args=args)


class TestQuizQuestionCreateView:
    url = _url("create")

    def test_create_for_friend(self, alice_client, alice, bob, friendship):
        resp = alice_client.post(self.url, {
            "target_user_id": bob.id,
            "question": "What is my favorite color?",
            "correct_answer": "blue",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == 0
        assert QuizQuestion.objects.filter(creator=alice, target_user=bob).exists()

    def test_creates_notification(self, alice_client, bob, friendship):
        alice_client.post(self.url, {
            "target_user_id": bob.id,
            "question": "Q?", "correct_answer": "A",
        })
        assert Notification.objects.filter(
            recipient=bob,
            notification_type=Notification.Type.QUIZ_INVITE,
        ).exists()

    def test_cannot_create_for_non_friend(self, alice_client, charlie):
        resp = alice_client.post(self.url, {
            "target_user_id": charlie.id,
            "question": "Q?", "correct_answer": "A",
        })
        assert resp.status_code == 400

    def test_cannot_create_for_self(self, alice_client, alice):
        resp = alice_client.post(self.url, {
            "target_user_id": alice.id,
            "question": "Q?", "correct_answer": "A",
        })
        assert resp.status_code == 400

    def test_non_existent_target(self, alice_client):
        resp = alice_client.post(self.url, {
            "target_user_id": 99999,
            "question": "Q?", "correct_answer": "A",
        })
        assert resp.status_code == 400

    def test_missing_fields(self, alice_client, bob, friendship):
        resp = alice_client.post(self.url, {"target_user_id": bob.id})
        assert resp.status_code == 400

        resp = alice_client.post(self.url, {"question": "Q?"})
        assert resp.status_code == 400

    def test_requires_auth(self, client, bob, friendship):
        resp = client.post(self.url, {
            "target_user_id": bob.id, "question": "Q?", "correct_answer": "A",
        })
        assert resp.status_code == 403

    def test_inactive_plugin(self, alice_client, bob, friendship):
        Plugin.objects.filter(plugin_type="quiz").update(is_active=False)
        resp = alice_client.post(self.url, {
            "target_user_id": bob.id, "question": "Q?", "correct_answer": "A",
        })
        assert resp.status_code == 404


class TestQuizReceivedQuestionsView:
    url = _url("received")

    def test_empty_when_no_questions(self, alice_client):
        resp = alice_client.get(self.url)
        assert resp.status_code == 200
        assert resp.json()["data"]["total"] == 0

    def test_lists_received_questions(self, alice_client, alice, bob, friendship):
        q = QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q?", correct_answer="A")
        resp = alice_client.get(self.url)
        ids = [item["id"] for item in resp.json()["data"]["results"]]
        assert q.id in ids

    def test_does_not_include_own_questions(self, alice_client, alice, bob, friendship):
        QuizQuestion.objects.create(creator=alice, target_user=bob, question="Q?", correct_answer="A")
        resp = alice_client.get(self.url)
        assert resp.json()["data"]["total"] == 0

    def test_default_filters_unanswered(self, alice_client, alice, bob, friendship):
        q1 = QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q1", correct_answer="A")
        q2 = QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q2", correct_answer="B")
        QuizAnswer.objects.create(question=q2, answerer=alice, answer="B", is_correct=True)
        resp = alice_client.get(self.url)
        ids = [item["id"] for item in resp.json()["data"]["results"]]
        assert q1.id in ids
        assert q2.id not in ids

    def test_filter_answered(self, alice_client, alice, bob, friendship):
        q1 = QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q1", correct_answer="A")
        QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q2", correct_answer="B")
        QuizAnswer.objects.create(question=q1, answerer=alice, answer="A", is_correct=True)
        resp = alice_client.get(self.url, {"answered": "true"})
        ids = [item["id"] for item in resp.json()["data"]["results"]]
        assert q1.id in ids
        assert len(ids) == 1

    def test_pagination(self, alice_client, alice, bob, friendship):
        for i in range(25):
            QuizQuestion.objects.create(creator=bob, target_user=alice, question=f"Q{i}", correct_answer="A")
        resp = alice_client.get(self.url, {"page_size": 10, "page": 2})
        assert resp.json()["data"]["page"] == 2
        assert len(resp.json()["data"]["results"]) == 10

    def test_requires_auth(self, client):
        resp = client.get(self.url)
        assert resp.status_code == 403

    def test_inactive_plugin(self, alice_client):
        Plugin.objects.filter(plugin_type="quiz").update(is_active=False)
        resp = alice_client.get(self.url)
        assert resp.status_code == 404

    def test_response_has_from_user_info(self, alice_client, alice, bob, friendship):
        QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q?", correct_answer="A")
        resp = alice_client.get(self.url)
        item = resp.json()["data"]["results"][0]
        assert "from_user" in item
        assert item["from_user"]["user_id"] == bob.id
        assert "nickname" in item["from_user"]


class TestQuizAnswerView:
    def test_answer_correct(self, alice_client, alice, bob, friendship):
        q = QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q?", correct_answer="right")
        resp = alice_client.post(_url("answer", q.id), {"answer": "right"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["data"]["is_correct"] is True
        assert data["data"]["correct_answer"] == "right"

    def test_answer_wrong(self, alice_client, alice, bob, friendship):
        q = QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q?", correct_answer="right")
        resp = alice_client.post(_url("answer", q.id), {"answer": "wrong"})
        assert resp.status_code == 201
        assert resp.json()["data"]["is_correct"] is False

    def test_cannot_answer_own_question(self, alice_client, alice, bob, friendship):
        q = QuizQuestion.objects.create(creator=alice, target_user=bob, question="Q?", correct_answer="A")
        resp = alice_client.post(_url("answer", q.id), {"answer": "A"})
        assert resp.status_code == 404

    def test_already_answered(self, alice_client, alice, bob, friendship):
        q = QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q?", correct_answer="A")
        QuizAnswer.objects.create(question=q, answerer=alice, answer="A", is_correct=True)
        resp = alice_client.post(_url("answer", q.id), {"answer": "A"})
        assert resp.status_code == 400
        assert "已作答" in resp.json()["message"]

    def test_non_existent_question(self, alice_client):
        resp = alice_client.post(_url("answer", 99999), {"answer": "test"})
        assert resp.status_code == 404

    def test_requires_auth(self, client, alice, bob, friendship):
        q = QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q?", correct_answer="A")
        resp = client.post(_url("answer", q.id), {"answer": "A"})
        assert resp.status_code == 403

    def test_inactive_plugin(self, alice_client, alice, bob, friendship):
        Plugin.objects.filter(plugin_type="quiz").update(is_active=False)
        q = QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q?", correct_answer="A")
        resp = alice_client.post(_url("answer", q.id), {"answer": "A"})
        assert resp.status_code == 404

    def test_creates_quizresult(self, alice_client, alice, bob, friendship):
        q = QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q?", correct_answer="right")
        alice_client.post(_url("answer", q.id), {"answer": "right"})
        result = QuizResult.objects.filter(
            user_a=alice, user_b=bob
        ).first()
        assert result is not None

    def test_match_score_after_both_answer(self, alice_client, bob_client, alice, bob, friendship):
        q1 = QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q1", correct_answer="A")
        QuizAnswer.objects.create(question=q1, answerer=alice, answer="A", is_correct=True)
        q2 = QuizQuestion.objects.create(creator=alice, target_user=bob, question="Q2", correct_answer="B")
        resp = bob_client.post(_url("answer", q2.id), {"answer": "B"})
        assert resp.status_code == 201
        result = QuizResult.objects.get(user_a=alice, user_b=bob)
        assert result.total_questions == 2
        assert result.correct_count == 2
        assert result.match_score == 100.0


class TestQuizQuestionDeleteView:
    def test_creator_can_delete(self, alice_client, alice, bob, friendship):
        q = QuizQuestion.objects.create(creator=alice, target_user=bob, question="Q?", correct_answer="A")
        resp = alice_client.delete(_url("delete", q.id))
        assert resp.status_code == 200
        assert not QuizQuestion.objects.filter(id=q.id).exists()

    def test_others_cannot_delete(self, alice_client, bob_client, alice, bob, friendship):
        q = QuizQuestion.objects.create(creator=bob, target_user=alice, question="Q?", correct_answer="A")
        resp = alice_client.delete(_url("delete", q.id))
        assert resp.status_code == 404
        assert QuizQuestion.objects.filter(id=q.id).exists()

    def test_non_existent(self, alice_client):
        resp = alice_client.delete(_url("delete", 99999))
        assert resp.status_code == 404

    def test_requires_auth(self, client, alice, bob, friendship):
        q = QuizQuestion.objects.create(creator=alice, target_user=bob, question="Q?", correct_answer="A")
        resp = client.delete(_url("delete", q.id))
        assert resp.status_code == 403

    def test_inactive_plugin(self, alice_client, alice, bob, friendship):
        Plugin.objects.filter(plugin_type="quiz").update(is_active=False)
        q = QuizQuestion.objects.create(creator=alice, target_user=bob, question="Q?", correct_answer="A")
        resp = alice_client.delete(_url("delete", q.id))
        assert resp.status_code == 404


class TestQuizResultView:
    def test_get_result(self, alice_client, bob_client, alice, bob, friendship):
        QuizResult.objects.create(
            user_a=alice, user_b=bob, total_questions=5, correct_count=4, match_score=80.0
        )
        resp = alice_client.get(_url("result", bob.id))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert float(data["match_score"]) == 80.0
        assert data["total_questions"] == 5

    def test_friend_id_in_response(self, alice_client, bob_client, alice, bob, friendship):
        QuizResult.objects.create(user_a=alice, user_b=bob, match_score=50.0)
        resp = alice_client.get(_url("result", bob.id))
        assert resp.json()["data"]["friend_id"] == bob.id

        resp = bob_client.get(_url("result", alice.id))
        assert resp.json()["data"]["friend_id"] == alice.id

    def test_no_result(self, alice_client, bob, friendship):
        resp = alice_client.get(_url("result", bob.id))
        assert resp.status_code == 404
        assert resp.json()["code"] == 40004

    def test_requires_auth(self, client, alice, bob, friendship):
        QuizResult.objects.create(user_a=alice, user_b=bob, match_score=50.0)
        resp = client.get(_url("result", bob.id))
        assert resp.status_code == 403

    def test_inactive_plugin(self, alice_client, bob, friendship):
        Plugin.objects.filter(plugin_type="quiz").update(is_active=False)
        resp = alice_client.get(_url("result", bob.id))
        assert resp.status_code == 404


class TestQuizLeaderboardView:
    url = _url("leaderboard")

    def test_returns_rankings(self, alice_client, alice, bob, friendship):
        QuizResult.objects.create(user_a=alice, user_b=bob, total_questions=10, correct_count=8, match_score=80.0)
        resp = alice_client.get(self.url)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["rankings"]) == 1
        rank = data["rankings"][0]
        assert rank["friend_id"] == bob.id
        assert rank["nickname"] == bob.nickname
        assert rank["match_score"] == 80.0
        assert rank["total_questions"] == 10
        assert rank["rank"] == 1

    def test_avg_match_rate(self, alice_client, alice, bob, charlie, friendship):
        Friendship.objects.create(from_user=alice, to_user=charlie, status="accepted")
        QuizResult.objects.create(user_a=alice, user_b=bob, match_score=90.0)
        QuizResult.objects.create(user_a=alice, user_b=charlie, match_score=70.0)
        resp = alice_client.get(self.url)
        assert resp.json()["data"]["avg_match_rate"] == 80.0

    def test_excludes_non_friend_results(self, alice_client, alice, bob, charlie, friendship):
        QuizResult.objects.create(user_a=alice, user_b=bob, match_score=90.0)
        QuizResult.objects.create(user_a=alice, user_b=charlie, match_score=70.0)
        resp = alice_client.get(self.url)
        assert len(resp.json()["data"]["rankings"]) == 1
        assert resp.json()["data"]["total_friends"] == 1

    def test_empty_returns_zero(self, alice_client):
        resp = alice_client.get(self.url)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["rankings"] == []
        assert data["avg_match_rate"] == 0
        assert data["total_friends"] == 0

    def test_sorted_by_score_desc(self, alice_client, alice, bob, charlie, friendship):
        Friendship.objects.create(from_user=alice, to_user=charlie, status="accepted")
        QuizResult.objects.create(user_a=alice, user_b=bob, match_score=80.0)
        QuizResult.objects.create(user_a=alice, user_b=charlie, match_score=95.0)
        resp = alice_client.get(self.url)
        scores = [r["match_score"] for r in resp.json()["data"]["rankings"]]
        assert scores == [95.0, 80.0]

    def test_requires_auth(self, client):
        resp = client.get(self.url)
        assert resp.status_code == 403

    def test_inactive_plugin(self, alice_client):
        Plugin.objects.filter(plugin_type="quiz").update(is_active=False)
        resp = alice_client.get(self.url)
        assert resp.status_code == 404

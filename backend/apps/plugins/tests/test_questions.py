import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.notifications.models import Notification
from apps.plugins.models import Plugin
from apps.plugins.questions.models import AnonymousQuestion

User = get_user_model()


@pytest.fixture(autouse=True)
def _active_plugin(db):
    Plugin.objects.get_or_create(plugin_type="question_box", defaults={"name": "匿名提问箱", "is_active": True})


@pytest.fixture
def stranger(db):
    return User.objects.create_user(username="stranger", password="Pass1234!")


def _url(name, *args):
    return reverse(f"question-{name}", args=args)


class TestQuestionCreateView:
    url = _url("create")

    def test_create_question(self, alice_client, bob):
        resp = alice_client.post(self.url, {"recipient_id": bob.id, "content": "Hello?"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == 0
        assert "id" in data["data"]
        assert AnonymousQuestion.objects.filter(recipient=bob, content="Hello?").exists()

    def test_creates_notification(self, alice_client, bob):
        alice_client.post(self.url, {"recipient_id": bob.id, "content": "Are you there?"})
        assert Notification.objects.filter(
            recipient=bob,
            notification_type=Notification.Type.ANONYMOUS_QUESTION,
        ).exists()

    def test_missing_recipient_id(self, alice_client):
        resp = alice_client.post(self.url, {"content": "Hello"})
        assert resp.status_code == 400

    def test_missing_content(self, alice_client, bob):
        resp = alice_client.post(self.url, {"recipient_id": bob.id})
        assert resp.status_code == 400

    def test_requires_auth(self, client, bob):
        resp = client.post(self.url, {"recipient_id": bob.id, "content": "test"})
        assert resp.status_code == 403

    def test_inactive_plugin_returns_404(self, alice_client, bob):
        Plugin.objects.filter(plugin_type="question_box").update(is_active=False)
        resp = alice_client.post(self.url, {"recipient_id": bob.id, "content": "test"})
        assert resp.status_code == 404

    def test_can_send_to_self(self, alice_client, alice):
        resp = alice_client.post(self.url, {"recipient_id": alice.id, "content": "self message"})
        assert resp.status_code == 201

    def test_content_strips_html_tags(self, alice_client, bob):
        resp = alice_client.post(self.url, {"recipient_id": bob.id, "content": "<script>alert('xss')</script>Hello"})
        assert resp.status_code == 201
        q = AnonymousQuestion.objects.get(recipient=bob)
        assert "<script>" not in q.content
        assert "</script>" not in q.content

    def test_default_is_public_true(self, alice_client, bob):
        resp = alice_client.post(self.url, {"recipient_id": bob.id, "content": "test"})
        assert resp.status_code == 201
        q = AnonymousQuestion.objects.get(recipient=bob)
        assert q.is_public is True

    def test_is_public_false(self, alice_client, bob):
        resp = alice_client.post(self.url, {"recipient_id": bob.id, "content": "private", "is_public": False})
        assert resp.status_code == 201
        q = AnonymousQuestion.objects.get(content="private")
        assert q.is_public is False


class TestInboxView:
    url = _url("inbox")

    def test_empty_inbox(self, alice_client):
        resp = alice_client.get(self.url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["total"] == 0
        assert data["data"]["results"] == []

    def test_lists_received_questions(self, alice_client, alice, stranger):
        q = AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="Q1")
        resp = alice_client.get(self.url)
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["data"]["results"]]
        assert q.id in ids

    def test_does_not_include_sent_questions(self, alice_client, alice, bob):
        AnonymousQuestion.objects.create(recipient=bob, sender=alice, content="Q to bob")
        resp = alice_client.get(self.url)
        assert resp.json()["data"]["total"] == 0

    def test_filter_answered_true(self, alice_client, alice, stranger):
        answered = AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="A", is_answered=True)
        AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="B", is_answered=False)
        resp = alice_client.get(self.url, {"answered": "true"})
        ids = [item["id"] for item in resp.json()["data"]["results"]]
        assert answered.id in ids
        assert len(ids) == 1

    def test_filter_answered_false(self, alice_client, alice, stranger):
        AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="A", is_answered=True)
        unanswered = AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="B")
        resp = alice_client.get(self.url, {"answered": "false"})
        ids = [item["id"] for item in resp.json()["data"]["results"]]
        assert unanswered.id in ids
        assert len(ids) == 1

    def test_order_by_newest_first(self, alice_client, alice, stranger):
        q1 = AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="Old")
        q2 = AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="New")
        resp = alice_client.get(self.url)
        ids = [item["id"] for item in resp.json()["data"]["results"]]
        assert ids == [q2.id, q1.id]

    def test_pagination(self, alice_client, alice, stranger):
        for i in range(25):
            AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content=f"Q{i}")
        resp = alice_client.get(self.url, {"page_size": 10, "page": 2})
        assert resp.json()["data"]["page"] == 2
        assert len(resp.json()["data"]["results"]) == 10

    def test_requires_auth(self, client):
        resp = client.get(self.url)
        assert resp.status_code == 403

    def test_inactive_plugin(self, alice_client):
        Plugin.objects.filter(plugin_type="question_box").update(is_active=False)
        resp = alice_client.get(self.url)
        assert resp.status_code == 404

    def test_non_staff_hides_sender(self, alice_client, alice, bob, stranger):
        AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="secret")
        resp = alice_client.get(self.url)
        item = resp.json()["data"]["results"][0]
        assert "real_sender" not in item
        assert "sender" not in item

    def test_staff_sees_sender(self, alice_client, alice, bob, stranger):
        alice.is_staff = True
        alice.save()
        AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="secret")
        resp = alice_client.get(self.url)
        item = resp.json()["data"]["results"][0]
        assert "real_sender" in item
        assert item["real_sender"]["user_id"] == stranger.id


class TestAnswerView:
    def test_answer_own_question(self, alice_client, alice, stranger):
        q = AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="Q")
        resp = alice_client.post(_url("answer", q.id), {"answer": "My answer"})
        assert resp.status_code == 200
        q.refresh_from_db()
        assert q.is_answered is True
        assert q.answer == "My answer"
        assert q.answered_at is not None

    def test_cannot_answer_others_question(self, alice_client, bob, stranger):
        q = AnonymousQuestion.objects.create(recipient=bob, sender=stranger, content="Q")
        resp = alice_client.post(_url("answer", q.id), {"answer": "hack"})
        assert resp.status_code == 404

    def test_non_existent_question(self, alice_client):
        resp = alice_client.post(_url("answer", 99999), {"answer": "test"})
        assert resp.status_code == 404

    def test_missing_answer_field(self, alice_client, alice, stranger):
        q = AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="Q")
        resp = alice_client.post(_url("answer", q.id), {})
        assert resp.status_code == 400

    def test_requires_auth(self, client, alice, stranger):
        q = AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="Q")
        resp = client.post(_url("answer", q.id), {"answer": "test"})
        assert resp.status_code == 403

    def test_inactive_plugin(self, alice_client, alice, stranger):
        Plugin.objects.filter(plugin_type="question_box").update(is_active=False)
        q = AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="Q")
        resp = alice_client.post(_url("answer", q.id), {"answer": "test"})
        assert resp.status_code == 404


class TestQuestionDeleteView:
    def test_recipient_can_delete(self, alice_client, alice, stranger):
        q = AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="Q")
        resp = alice_client.delete(_url("delete", q.id))
        assert resp.status_code == 200
        assert not AnonymousQuestion.objects.filter(id=q.id).exists()

    def test_others_cannot_delete(self, alice_client, bob, stranger):
        q = AnonymousQuestion.objects.create(recipient=bob, sender=stranger, content="Q")
        resp = alice_client.delete(_url("delete", q.id))
        assert resp.status_code == 404
        assert AnonymousQuestion.objects.filter(id=q.id).exists()

    def test_non_existent(self, alice_client):
        resp = alice_client.delete(_url("delete", 99999))
        assert resp.status_code == 404

    def test_requires_auth(self, client, alice, stranger):
        q = AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="Q")
        resp = client.delete(_url("delete", q.id))
        assert resp.status_code == 403

    def test_inactive_plugin(self, alice_client, alice, stranger):
        Plugin.objects.filter(plugin_type="question_box").update(is_active=False)
        q = AnonymousQuestion.objects.create(recipient=alice, sender=stranger, content="Q")
        resp = alice_client.delete(_url("delete", q.id))
        assert resp.status_code == 404

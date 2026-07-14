import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status

from apps.admin_dashboard.models import SiteLog, SiteSettings
from apps.chat.models import ChatRoom, ChatRoomMember, Message
from apps.feed.models import Comment, Post
from apps.friends.models import Friendship
from apps.groups.models import InterestGroup, GroupMember
from apps.plugins.models import Plugin
from apps.plugins.questions.models import AnonymousQuestion
from apps.plugins.quizzes.models import QuizQuestionBank, QuizQuestionBankOption, QuizSubmission, QuizSubmissionAnswer, QuizTest, QuizTestOption, QuizTestQuestion
from apps.profiles.models import VisitRecord

User = get_user_model()

URL = "/api/v1/admin"


# ── helpers ────────────────────────────────────────────────────

def assert_ok(response):
    resp = response.json()
    assert resp["code"] == 0
    return resp.get("data")


def assert_forbidden(response):
    """Assert 403 – accepts both DRF-native (code=40300) and custom api_response (code=40003)."""
    assert response.status_code == status.HTTP_403_FORBIDDEN
    resp = response.json()
    assert resp["code"] in (40300, 40003)


def assert_staff_denied(response):
    """Assert 403 from the view's own check_admin (authenticated but not staff)."""
    assert response.status_code == status.HTTP_403_FORBIDDEN
    resp = response.json()
    assert resp["code"] == 40003
    assert resp["message"] == "无权访问"


def assert_not_found(response):
    assert response.status_code == status.HTTP_404_NOT_FOUND
    resp = response.json()
    assert resp["code"] == 40004


# ── additional fixtures ────────────────────────────────────────

@pytest.fixture
def comment(alice, alice_post):
    return Comment.objects.create(post=alice_post, author=alice, content="Alice comment")


@pytest.fixture
def bob_comment(bob, bob_post):
    return Comment.objects.create(post=bob_post, author=bob, content="Bob comment")


@pytest.fixture
def plugin_entry(db):
    return Plugin.objects.create(
        name="Questions", plugin_type="questions", is_active=True, config={"key": "val"}
    )


@pytest.fixture
def inactive_plugin(db):
    return Plugin.objects.create(
        name="Quizzes", plugin_type="quizzes", is_active=False, config={}
    )


@pytest.fixture
def site_setting(db):
    SiteSettings.objects.create(key="site_name", value="My Site")
    SiteSettings.objects.create(key="maintenance_mode", value=False)
    return SiteSettings.objects.all()


@pytest.fixture
def chat_room(alice, bob):
    room = ChatRoom.objects.create(room_type="private")
    ChatRoomMember.objects.create(room=room, user=alice)
    ChatRoomMember.objects.create(room=room, user=bob)
    return room


@pytest.fixture
def msg(chat_room, alice):
    return Message.objects.create(room=chat_room, sender=alice, content="Hello")


@pytest.fixture
def visit_record(alice, bob):
    return VisitRecord.objects.create(visitor=alice, visited_user=bob)


@pytest.fixture
def question(admin_user, alice):
    return AnonymousQuestion.objects.create(
        recipient=admin_user, sender=alice, content="Is this anonymous?"
    )


@pytest.fixture
def quiz_test(admin_user):
    test = QuizTest.objects.create(
        owner=admin_user,
        title="Favorite color test",
        status=QuizTest.Status.PUBLISHED,
        published_at=timezone.now(),
    )
    question = QuizTestQuestion.objects.create(test=test, question_text="Favorite color?", order=1)
    option = QuizTestOption.objects.create(question=question, option_text="Blue", order=1)
    QuizTestOption.objects.create(question=question, option_text="Red", order=2)
    question.correct_option = option
    question.save(update_fields=["correct_option"])
    return test


@pytest.fixture
def quiz_submission(quiz_test, bob):
    question = quiz_test.questions.first()
    submission = QuizSubmission.objects.create(
        test=quiz_test,
        participant_type=QuizSubmission.ParticipantType.USER,
        user=bob,
        participant_name=bob.nickname,
        correct_count=1,
        score_percent=100,
        title="灵魂拍档",
    )
    QuizSubmissionAnswer.objects.create(
        submission=submission,
        question=question,
        selected_option=question.correct_option,
        is_correct=True,
    )
    return submission


@pytest.fixture
def site_log(staff_user):
    return SiteLog.objects.create(
        user=staff_user, action="test_action", detail={"test": True},
        ip_address="127.0.0.1",
    )


@pytest.fixture
def group_post(test_group, alice):
    return Post.objects.create(author=alice, content="Group post", group=test_group)


# ═══════════════════════════════════════════════════════════════
#  Permission enforcement
# ═══════════════════════════════════════════════════════════════

class TestPermissionRequired:
    def test_unauthenticated_users(self, client):
        assert_forbidden(client.get(f"{URL}/users/"))
        assert_forbidden(client.get(f"{URL}/posts/"))
        assert_forbidden(client.get(f"{URL}/comments/"))
        assert_forbidden(client.get(f"{URL}/anonymous-questions/"))
        assert_forbidden(client.get(f"{URL}/quiz/tests/"))
        assert_forbidden(client.get(f"{URL}/plugins/"))
        assert_forbidden(client.get(f"{URL}/plugins/configs/"))
        assert_forbidden(client.get(f"{URL}/settings/"))
        assert_forbidden(client.get(f"{URL}/stats/"))
        assert_forbidden(client.get(f"{URL}/logs/"))
        assert_forbidden(client.get(f"{URL}/logs/actions/"))
        assert_forbidden(client.get(f"{URL}/trends/"))
        assert_forbidden(client.get(f"{URL}/groups/"))

    def test_regular_user_gets_403(self, alice_client):
        assert_staff_denied(alice_client.get(f"{URL}/users/"))
        assert_staff_denied(alice_client.get(f"{URL}/posts/"))
        assert_staff_denied(alice_client.get(f"{URL}/comments/"))
        assert_staff_denied(alice_client.get(f"{URL}/anonymous-questions/"))
        assert_staff_denied(alice_client.get(f"{URL}/quiz/tests/"))
        assert_staff_denied(alice_client.get(f"{URL}/plugins/"))
        assert_staff_denied(alice_client.get(f"{URL}/plugins/configs/"))
        assert_staff_denied(alice_client.get(f"{URL}/settings/"))
        assert_staff_denied(alice_client.get(f"{URL}/stats/"))
        assert_staff_denied(alice_client.get(f"{URL}/logs/"))
        assert_staff_denied(alice_client.get(f"{URL}/logs/actions/"))
        assert_staff_denied(alice_client.get(f"{URL}/trends/"))
        assert_staff_denied(alice_client.get(f"{URL}/groups/"))

    def test_regular_user_mutation_endpoints(self, alice_client, bob, alice_post, comment, plugin_entry, test_group):
        assert_staff_denied(alice_client.patch(f"{URL}/users/{bob.pk}/", {"is_active": False}, format="json"))
        assert_staff_denied(alice_client.delete(f"{URL}/posts/{alice_post.pk}/"))
        assert_staff_denied(alice_client.delete(f"{URL}/comments/{comment.pk}/"))
        assert_staff_denied(alice_client.patch(f"{URL}/plugins/{plugin_entry.pk}/", {"is_active": False}, format="json"))
        assert_staff_denied(alice_client.delete(f"{URL}/groups/{test_group.pk}/"))

    def test_regular_user_group_posts(self, alice_client, test_group):
        assert_staff_denied(alice_client.get(f"{URL}/groups/{test_group.pk}/posts/"))

    def test_regular_user_quiz_admin_endpoints(self, alice_client, quiz_test, quiz_submission):
        assert_staff_denied(alice_client.get(f"{URL}/quiz/tests/{quiz_test.pk}/"))
        assert_staff_denied(alice_client.delete(f"{URL}/quiz/tests/{quiz_test.pk}/"))
        assert_staff_denied(alice_client.get(f"{URL}/quiz/submissions/"))
        assert_staff_denied(alice_client.get(f"{URL}/quiz/submissions/{quiz_submission.pk}/"))
        assert_staff_denied(alice_client.delete(f"{URL}/quiz/submissions/{quiz_submission.pk}/"))
        assert_staff_denied(alice_client.post(
            f"{URL}/quiz/question-bank/",
            {"question_text": "test", "options": [{"option_text": "A", "order": 1}, {"option_text": "B", "order": 2}]},
            format="json",
        ))
        assert_staff_denied(alice_client.get(f"{URL}/quiz/stats/"))


# ═══════════════════════════════════════════════════════════════
#  1. AdminUserListView
# ═══════════════════════════════════════════════════════════════

class TestAdminUserListView:
    def test_list_all(self, staff_client, alice, bob, charlie):
        data = assert_ok(staff_client.get(f"{URL}/users/"))
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total"] >= 3
        usernames = {u["username"] for u in data["results"]}
        assert usernames.issuperset({"alice", "bob", "charlie"})

    def test_search_username(self, staff_client, alice, bob, charlie):
        data = assert_ok(staff_client.get(f"{URL}/users/?search=bob"))
        assert data["total"] == 1
        assert data["results"][0]["username"] == "bob"

    def test_search_nickname(self, staff_client, alice, bob, charlie):
        data = assert_ok(staff_client.get(f"{URL}/users/?search=Charlie"))
        assert data["total"] == 1
        assert data["results"][0]["nickname"] == "Charlie"

    def test_search_no_match(self, staff_client):
        data = assert_ok(staff_client.get(f"{URL}/users/?search=nonexistent"))
        assert data["total"] == 0
        assert data["results"] == []

    def test_pagination_out_of_range(self, staff_client):
        data = assert_ok(staff_client.get(f"{URL}/users/?page=999"))
        assert data["results"] == []

    def test_response_shape(self, staff_client):
        data = assert_ok(staff_client.get(f"{URL}/users/"))
        if data["results"]:
            u = data["results"][0]
            for key in ("id", "username", "nickname", "email", "is_active", "is_staff", "is_superuser", "date_joined", "last_login"):
                assert key in u


# ═══════════════════════════════════════════════════════════════
#  2. AdminUserUpdateView
# ═══════════════════════════════════════════════════════════════

class TestAdminUserUpdateView:
    def test_staff_toggle_is_active(self, staff_client, staff_user, alice):
        assert alice.is_active is True
        data = assert_ok(staff_client.patch(f"{URL}/users/{alice.pk}/", {"is_active": False}, format="json"))
        assert data["is_active"] is False
        alice.refresh_from_db()
        assert alice.is_active is False
        assert SiteLog.objects.filter(action="update_user", user=staff_user).exists()

    def test_staff_cannot_set_is_staff(self, staff_client, alice):
        assert_ok(staff_client.patch(f"{URL}/users/{alice.pk}/", {"is_staff": True}, format="json"))
        alice.refresh_from_db()
        assert alice.is_staff is False

    def test_superuser_can_set_is_staff(self, admin_client, admin_user, alice):
        assert alice.is_staff is False
        data = assert_ok(admin_client.patch(f"{URL}/users/{alice.pk}/", {"is_staff": True}, format="json"))
        assert data["is_staff"] is True
        alice.refresh_from_db()
        assert alice.is_staff is True
        assert SiteLog.objects.filter(action="update_user", user=admin_user).exists()

    def test_non_existent_user(self, staff_client):
        resp = staff_client.patch(f"{URL}/users/99999/", {"is_active": False}, format="json")
        assert_not_found(resp)
        assert resp.json()["message"] == "用户不存在"

    def test_site_log_detail(self, staff_client, staff_user, alice):
        SiteLog.objects.all().delete()
        staff_client.patch(f"{URL}/users/{alice.pk}/", {"is_active": False}, format="json")
        log = SiteLog.objects.get(action="update_user")
        assert log.user == staff_user
        assert log.detail["user_id"] == alice.pk
        assert log.ip_address is not None


# ═══════════════════════════════════════════════════════════════
#  3. AdminPostListView
# ═══════════════════════════════════════════════════════════════

class TestAdminPostListView:
    def test_list_all(self, staff_client, alice_post, bob_post):
        data = assert_ok(staff_client.get(f"{URL}/posts/"))
        assert data["total"] >= 2
        contents = {r["content"] for r in data["results"]}
        assert contents.issuperset({"Hello from Alice", "Hello from Bob"})

    def test_response_shape(self, staff_client, alice_post):
        data = assert_ok(staff_client.get(f"{URL}/posts/"))
        item = data["results"][0]
        for key in ("id", "author_nickname", "content", "visibility", "topic_tag", "created_at"):
            assert key in item


# ═══════════════════════════════════════════════════════════════
#  4. AdminPostDeleteView
# ═══════════════════════════════════════════════════════════════

class TestAdminPostDeleteView:
    def test_staff_delete_any_post(self, staff_client, staff_user, alice_post):
        pk = alice_post.pk
        assert_ok(staff_client.delete(f"{URL}/posts/{pk}/"))
        assert not Post.objects.filter(pk=pk).exists()
        assert SiteLog.objects.filter(action="delete_post", user=staff_user).exists()

    def test_site_log_detail(self, staff_client, bob_post):
        SiteLog.objects.all().delete()
        staff_client.delete(f"{URL}/posts/{bob_post.pk}/")
        log = SiteLog.objects.get(action="delete_post")
        assert log.detail["post_id"] == bob_post.pk

    def test_non_existent(self, staff_client):
        resp = staff_client.delete(f"{URL}/posts/99999/")
        assert_not_found(resp)
        assert resp.json()["message"] == "动态不存在"
        assert Post.objects.count() >= 0


# ═══════════════════════════════════════════════════════════════
#  5. AdminCommentListView
# ═══════════════════════════════════════════════════════════════

class TestAdminCommentListView:
    def test_list_all(self, staff_client, comment, bob_comment):
        data = assert_ok(staff_client.get(f"{URL}/comments/"))
        assert data["total"] >= 2
        contents = {r["content"] for r in data["results"]}
        assert contents.issuperset({"Alice comment", "Bob comment"})

    def test_response_shape(self, staff_client, comment):
        data = assert_ok(staff_client.get(f"{URL}/comments/"))
        item = data["results"][0]
        for key in ("id", "post", "post_content", "author_nickname", "content", "parent", "created_at"):
            assert key in item


# ═══════════════════════════════════════════════════════════════
#  6. AdminCommentDeleteView
# ═══════════════════════════════════════════════════════════════

class TestAdminCommentDeleteView:
    def test_staff_delete_any_comment(self, staff_client, staff_user, comment):
        pk = comment.pk
        assert_ok(staff_client.delete(f"{URL}/comments/{pk}/"))
        assert not Comment.objects.filter(pk=pk).exists()
        assert SiteLog.objects.filter(action="delete_comment", user=staff_user).exists()

    def test_site_log_detail(self, staff_client, comment):
        SiteLog.objects.all().delete()
        staff_client.delete(f"{URL}/comments/{comment.pk}/")
        log = SiteLog.objects.get(action="delete_comment")
        assert log.detail["comment_id"] == comment.pk

    def test_non_existent(self, staff_client):
        resp = staff_client.delete(f"{URL}/comments/99999/")
        assert_not_found(resp)
        assert resp.json()["message"] == "评论不存在"


# ═══════════════════════════════════════════════════════════════
#  7. AdminAnonymousQuestionsView
# ═══════════════════════════════════════════════════════════════

class TestAdminAnonymousQuestionsView:
    def test_list(self, staff_client, question):
        data = assert_ok(staff_client.get(f"{URL}/anonymous-questions/"))
        assert data["total"] >= 1
        item = data["results"][0]
        assert item["content"] == "Is this anonymous?"

    def test_shows_sender_identity(self, staff_client, question):
        data = assert_ok(staff_client.get(f"{URL}/anonymous-questions/"))
        item = data["results"][0]
        assert item["real_sender"]["user_id"] is not None
        assert item["real_sender"]["nickname"] == "Alice"

    def test_response_shape(self, staff_client, question):
        data = assert_ok(staff_client.get(f"{URL}/anonymous-questions/"))
        item = data["results"][0]
        for key in ("id", "recipient", "recipient_nickname", "real_sender", "content",
                     "answer", "is_answered", "is_public", "created_at"):
            assert key in item

    def test_empty(self, staff_client):
        data = assert_ok(staff_client.get(f"{URL}/anonymous-questions/"))
        assert data["total"] == 0


# ═══════════════════════════════════════════════════════════════
#  8. AdminQuizQuestionsView
# ═══════════════════════════════════════════════════════════════

class TestAdminQuizQuestionsView:
    def test_list_with_submission_count(self, staff_client, quiz_test, quiz_submission):
        data = assert_ok(staff_client.get(f"{URL}/quiz/tests/"))
        assert data["total"] >= 1
        item = data["results"][0]
        assert item["title"] == "Favorite color test"
        assert item["question_count"] == 1
        assert item["submission_count"] == 1

    def test_test_without_submission(self, staff_client, quiz_test):
        data = assert_ok(staff_client.get(f"{URL}/quiz/tests/"))
        item = data["results"][0]
        assert item["submission_count"] == 0

    def test_response_shape(self, staff_client, quiz_test):
        data = assert_ok(staff_client.get(f"{URL}/quiz/tests/"))
        item = data["results"][0]
        for key in ("id", "owner", "title", "status", "question_count", "submission_count", "created_at", "published_at"):
            assert key in item
        assert "user_id" in item["owner"]
        assert "nickname" in item["owner"]

    def test_detail_shows_standard_answer(self, staff_client, quiz_test):
        data = assert_ok(staff_client.get(f"{URL}/quiz/tests/{quiz_test.id}/"))
        question = data["questions"][0]
        assert question["question_text"] == "Favorite color?"
        assert question["correct_option_id"] == quiz_test.questions.first().correct_option_id

    def test_delete_test_is_soft_delete(self, staff_client, quiz_test):
        assert_ok(staff_client.delete(f"{URL}/quiz/tests/{quiz_test.id}/"))
        quiz_test.refresh_from_db()
        assert quiz_test.status == QuizTest.Status.DELETED
        assert quiz_test.deleted_at is not None

    def test_submission_list_and_detail(self, staff_client, quiz_submission):
        data = assert_ok(staff_client.get(f"{URL}/quiz/submissions/"))
        assert data["total"] >= 1
        assert data["results"][0]["test_title"] == "Favorite color test"

        detail = assert_ok(staff_client.get(f"{URL}/quiz/submissions/{quiz_submission.id}/"))
        assert detail["answers"][0]["selected_option_id"] == quiz_submission.answers.first().selected_option_id
        assert detail["answers"][0]["correct_option_id"] == quiz_submission.answers.first().question.correct_option_id

    def test_delete_submission_is_soft_delete(self, staff_client, quiz_submission):
        assert_ok(staff_client.delete(f"{URL}/quiz/submissions/{quiz_submission.id}/"))
        quiz_submission.refresh_from_db()
        assert quiz_submission.is_deleted is True

    def test_question_bank_crud_and_delete_keeps_test_snapshot(self, staff_client, quiz_test):
        payload = {
            "question_text": "Bank question?",
            "tags": ["daily"],
            "options": [
                {"option_text": "A", "order": 1},
                {"option_text": "B", "order": 2},
            ],
        }
        created = assert_ok(staff_client.post(f"{URL}/quiz/question-bank/", payload, format="json"))
        bank_id = created["id"]
        assert QuizQuestionBank.objects.filter(pk=bank_id).exists()

        updated = assert_ok(staff_client.patch(
            f"{URL}/quiz/question-bank/{bank_id}/",
            {**payload, "question_text": "Updated bank question?"},
            format="json",
        ))
        assert updated["question_text"] == "Updated bank question?"

        test_question = quiz_test.questions.first()
        test_question.source_bank_question_id = bank_id
        test_question.save(update_fields=["source_bank_question"])
        assert_ok(staff_client.delete(f"{URL}/quiz/question-bank/{bank_id}/"))
        test_question.refresh_from_db()
        assert test_question.question_text == "Favorite color?"
        assert test_question.source_bank_question_id is None

    def test_question_bank_list_filters_by_tag(self, staff_client):
        daily = QuizQuestionBank.objects.create(question_text="Daily bank question?", tags=["daily"])
        QuizQuestionBankOption.objects.bulk_create([
            QuizQuestionBankOption(bank_question=daily, option_text="A", order=1),
            QuizQuestionBankOption(bank_question=daily, option_text="B", order=2),
        ])
        social = QuizQuestionBank.objects.create(question_text="Social bank question?", tags=["social"])
        QuizQuestionBankOption.objects.bulk_create([
            QuizQuestionBankOption(bank_question=social, option_text="A", order=1),
            QuizQuestionBankOption(bank_question=social, option_text="B", order=2),
        ])

        data = assert_ok(staff_client.get(f"{URL}/quiz/question-bank/", {"tag": "daily"}))

        assert [item["id"] for item in data["results"]] == [daily.id]

    def test_stats(self, staff_client, admin_user, quiz_test, quiz_submission):
        QuizTest.objects.create(owner=admin_user, title="Draft stats test", status=QuizTest.Status.DRAFT)
        QuizTest.objects.create(owner=admin_user, title="Deleted stats test", status=QuizTest.Status.DELETED)
        QuizSubmission.objects.create(
            test=quiz_test,
            participant_type=QuizSubmission.ParticipantType.VISITOR,
            participant_name="访客",
            correct_count=0,
            score_percent=0,
            title="神秘距离感",
        )
        QuizSubmission.objects.create(
            test=quiz_test,
            participant_type=QuizSubmission.ParticipantType.USER,
            user=admin_user,
            participant_name=admin_user.nickname,
            correct_count=0,
            score_percent=0,
            title="神秘距离感",
            is_deleted=True,
        )

        data = assert_ok(staff_client.get(f"{URL}/quiz/stats/"))
        assert data == {
            "total_tests": 3,
            "published_tests": 1,
            "draft_tests": 1,
            "deleted_tests": 1,
            "total_submissions": 2,
            "user_submissions": 1,
            "visitor_submissions": 1,
            "question_bank_count": 0,
        }


# ═══════════════════════════════════════════════════════════════
#  9. AdminPluginListView
# ═══════════════════════════════════════════════════════════════

class TestAdminPluginListView:
    def test_list(self, staff_client, plugin_entry, inactive_plugin):
        data = assert_ok(staff_client.get(f"{URL}/plugins/"))
        assert data["total"] >= 2
        types = {r["type"] for r in data["results"]}
        assert "questions" in types
        assert "quizzes" in types

    def test_response_shape(self, staff_client, plugin_entry):
        data = assert_ok(staff_client.get(f"{URL}/plugins/"))
        item = data["results"][0]
        for key in ("id", "name", "type", "is_active", "config", "created_at"):
            assert key in item


# ═══════════════════════════════════════════════════════════════
#  10. AdminPluginUpdateView
# ═══════════════════════════════════════════════════════════════

class TestAdminPluginUpdateView:
    def test_toggle_active(self, staff_client, staff_user, plugin_entry):
        assert plugin_entry.is_active is True
        data = assert_ok(staff_client.patch(f"{URL}/plugins/{plugin_entry.pk}/", {"is_active": False}, format="json"))
        assert data["is_active"] is False
        plugin_entry.refresh_from_db()
        assert plugin_entry.is_active is False
        assert SiteLog.objects.filter(action="update_plugin", user=staff_user).exists()

    def test_activate_inactive(self, staff_client, staff_user, inactive_plugin):
        assert inactive_plugin.is_active is False
        data = assert_ok(staff_client.patch(f"{URL}/plugins/{inactive_plugin.pk}/", {"is_active": True}, format="json"))
        assert data["is_active"] is True
        inactive_plugin.refresh_from_db()
        assert inactive_plugin.is_active is True

    def test_site_log_detail(self, staff_client, plugin_entry):
        SiteLog.objects.all().delete()
        staff_client.patch(f"{URL}/plugins/{plugin_entry.pk}/", {"is_active": False}, format="json")
        log = SiteLog.objects.get(action="update_plugin")
        assert log.detail["plugin_id"] == plugin_entry.pk
        assert log.detail["is_active"] is False

    def test_partial_update_no_key(self, staff_client, plugin_entry):
        data = assert_ok(staff_client.patch(f"{URL}/plugins/{plugin_entry.pk}/", {}, format="json"))
        assert data["is_active"] is plugin_entry.is_active
        assert SiteLog.objects.filter(action="update_plugin").exists()

    def test_non_existent(self, staff_client):
        resp = staff_client.patch(f"{URL}/plugins/99999/", {"is_active": False}, format="json")
        assert_not_found(resp)
        assert resp.json()["message"] == "插件不存在"


# ═══════════════════════════════════════════════════════════════
#  11. AdminPluginConfigView
# ═══════════════════════════════════════════════════════════════

class TestAdminPluginConfigView:
    def test_returns_list(self, staff_client):
        data = assert_ok(staff_client.get(f"{URL}/plugins/configs/"))
        assert isinstance(data, list)


# ═══════════════════════════════════════════════════════════════
#  12. AdminSettingsView
# ═══════════════════════════════════════════════════════════════

class TestAdminSettingsView:
    def test_get(self, staff_client, site_setting):
        data = assert_ok(staff_client.get(f"{URL}/settings/"))
        keys = {s["key"] for s in data}
        assert "site_name" in keys
        assert "maintenance_mode" in keys

    def test_get_empty(self, staff_client):
        data = assert_ok(staff_client.get(f"{URL}/settings/"))
        assert data == []

    def test_patch(self, staff_client, staff_user):
        assert_ok(staff_client.patch(f"{URL}/settings/", {"settings": {"site_name": "New Name"}}, format="json"))
        assert SiteSettings.objects.get(key="site_name").value == "New Name"
        assert SiteLog.objects.filter(action="update_settings", user=staff_user).exists()

    def test_patch_bulk(self, staff_client):
        SiteSettings.objects.create(key="site_name", value="Old")
        SiteSettings.objects.create(key="maintenance_mode", value=False)
        data = assert_ok(staff_client.patch(f"{URL}/settings/", {
            "settings": {"site_name": "Updated", "maintenance_mode": True}
        }, format="json"))
        keys = {s["key"] for s in data}
        assert "site_name" in keys
        assert "maintenance_mode" in keys
        assert SiteSettings.objects.get(key="maintenance_mode").value is True

    def test_patch_upsert(self, staff_client):
        assert_ok(staff_client.patch(f"{URL}/settings/", {"settings": {"new_key": "val"}}, format="json"))
        assert SiteSettings.objects.filter(key="new_key").exists()

    def test_patch_site_log_detail(self, staff_client):
        SiteLog.objects.all().delete()
        staff_client.patch(f"{URL}/settings/", {"settings": {"site_name": "Logged"}}, format="json")
        log = SiteLog.objects.get(action="update_settings")
        assert log.detail["settings"]["site_name"] == "Logged"

    def test_get_response_shape(self, staff_client, site_setting):
        data = assert_ok(staff_client.get(f"{URL}/settings/"))
        item = data[0]
        assert "key" in item
        assert "value" in item


# ═══════════════════════════════════════════════════════════════
#  13. AdminStatsView
# ═══════════════════════════════════════════════════════════════

class TestAdminStatsView:
    def test_stats(self, staff_client, alice, bob, alice_post, comment, msg):
        data = assert_ok(staff_client.get(f"{URL}/stats/"))
        assert data["total_users"] >= 2
        assert data["total_posts"] >= 1
        assert data["total_comments"] >= 1
        assert data["total_messages"] >= 1
        assert "active_users_today" in data

    def test_all_keys_present(self, staff_client):
        data = assert_ok(staff_client.get(f"{URL}/stats/"))
        for key in ("total_users", "total_posts", "total_comments", "total_messages", "active_users_today"):
            assert key in data


# ═══════════════════════════════════════════════════════════════
#  14. AdminLogsView
# ═══════════════════════════════════════════════════════════════

class TestAdminLogsView:
    def test_list(self, staff_client, site_log):
        data = assert_ok(staff_client.get(f"{URL}/logs/"))
        assert data["total"] >= 1
        assert data["results"][0]["action"] == "test_action"

    def test_response_shape(self, staff_client, site_log):
        data = assert_ok(staff_client.get(f"{URL}/logs/"))
        item = data["results"][0]
        for key in ("id", "admin_nickname", "action", "detail", "ip_address", "created_at"):
            assert key in item

    def test_filter_by_action(self, staff_client, staff_user):
        SiteLog.objects.create(user=staff_user, action="custom_action", detail={})
        data = assert_ok(staff_client.get(f"{URL}/logs/?action=custom_action"))
        assert data["total"] == 1
        for item in data["results"]:
            assert item["action"] == "custom_action"

    def test_filter_by_user_id(self, staff_client, staff_user, admin_user):
        SiteLog.objects.create(user=admin_user, action="admin_action", detail={})
        SiteLog.objects.create(user=staff_user, action="staff_action", detail={})
        data = assert_ok(staff_client.get(f"{URL}/logs/?user_id={admin_user.pk}"))
        assert data["total"] >= 1
        for item in data["results"]:
            assert item["admin_nickname"] == admin_user.nickname

    def test_filter_no_match(self, staff_client):
        data = assert_ok(staff_client.get(f"{URL}/logs/?action=nonexistent"))
        assert data["total"] == 0

    def test_empty(self, staff_client):
        SiteLog.objects.all().delete()
        data = assert_ok(staff_client.get(f"{URL}/logs/"))
        assert data["total"] == 0


# ═══════════════════════════════════════════════════════════════
#  15. AdminLogActionsView
# ═══════════════════════════════════════════════════════════════

class TestAdminLogActionsView:
    def test_list(self, staff_client, site_log):
        data = assert_ok(staff_client.get(f"{URL}/logs/actions/"))
        assert isinstance(data, list)
        assert "test_action" in data

    def test_distinct(self, staff_client, staff_user):
        SiteLog.objects.create(user=staff_user, action="dup", detail={})
        SiteLog.objects.create(user=staff_user, action="dup", detail={})
        SiteLog.objects.create(user=staff_user, action="unique", detail={})
        data = assert_ok(staff_client.get(f"{URL}/logs/actions/"))
        assert data.count("dup") == 1
        assert "unique" in data

    def test_empty(self, staff_client):
        SiteLog.objects.all().delete()
        data = assert_ok(staff_client.get(f"{URL}/logs/actions/"))
        assert data == []


# ═══════════════════════════════════════════════════════════════
#  16. AdminTrendsView
# ═══════════════════════════════════════════════════════════════

class TestAdminTrendsView:
    def test_shape(self, staff_client):
        data = assert_ok(staff_client.get(f"{URL}/trends/"))
        for key in ("days", "users", "posts", "messages", "comments", "visits", "friendships"):
            assert key in data
        assert data["days"] == 7

    def test_custom_days(self, staff_client):
        data = assert_ok(staff_client.get(f"{URL}/trends/?days=30"))
        assert data["days"] == 30

    def test_with_data(self, staff_client, alice, alice_post, comment, bob, msg, visit_record, friendship):
        data = assert_ok(staff_client.get(f"{URL}/trends/?days=30"))
        assert isinstance(data["users"], list)
        assert isinstance(data["posts"], list)
        assert isinstance(data["messages"], list)
        assert isinstance(data["comments"], list)
        assert isinstance(data["visits"], list)
        assert isinstance(data["friendships"], list)


# ═══════════════════════════════════════════════════════════════
#  17. AdminGroupListView
# ═══════════════════════════════════════════════════════════════

class TestAdminGroupListView:
    def test_list(self, staff_client, test_group):
        data = assert_ok(staff_client.get(f"{URL}/groups/"))
        assert data["total"] >= 1
        names = {r["name"] for r in data["results"]}
        assert "Test Group" in names

    def test_search(self, staff_client, test_group):
        data = assert_ok(staff_client.get(f"{URL}/groups/?search=Test"))
        assert data["total"] == 1
        assert data["results"][0]["name"] == "Test Group"

    def test_search_no_match(self, staff_client, test_group):
        data = assert_ok(staff_client.get(f"{URL}/groups/?search=Nonexistent"))
        assert data["total"] == 0

    def test_member_count(self, staff_client, test_group, group_member):
        data = assert_ok(staff_client.get(f"{URL}/groups/"))
        group_data = next(g for g in data["results"] if g["id"] == test_group.pk)
        assert group_data["member_count"] >= 1

    def test_response_shape(self, staff_client, test_group):
        data = assert_ok(staff_client.get(f"{URL}/groups/"))
        item = data["results"][0]
        for key in ("id", "name", "description", "cover_url", "is_public",
                     "creator_name", "member_count", "created_at"):
            assert key in item


# ═══════════════════════════════════════════════════════════════
#  18. AdminGroupDeleteView
# ═══════════════════════════════════════════════════════════════

class TestAdminGroupDeleteView:
    def test_staff_delete(self, staff_client, staff_user, test_group, group_member):
        pk = test_group.pk
        assert_ok(staff_client.delete(f"{URL}/groups/{pk}/"))
        assert not InterestGroup.objects.filter(pk=pk).exists()
        assert not GroupMember.objects.filter(group_id=pk).exists()
        assert SiteLog.objects.filter(action="delete_group", user=staff_user).exists()

    def test_cascading_cleanup(self, staff_client, test_group, group_member, group_post):
        """Deleting a group removes members, chat rooms, and unlinks posts."""
        from apps.chat.models import ChatRoom
        room = ChatRoom.objects.create(room_type="group", group=test_group)
        pk = test_group.pk
        staff_client.delete(f"{URL}/groups/{pk}/")
        assert not ChatRoom.objects.filter(group_id=pk).exists()
        assert not GroupMember.objects.filter(group_id=pk).exists()
        assert Post.objects.filter(pk=group_post.pk).first().group is None

    def test_site_log_detail(self, staff_client, test_group):
        SiteLog.objects.all().delete()
        staff_client.delete(f"{URL}/groups/{test_group.pk}/")
        log = SiteLog.objects.get(action="delete_group")
        assert log.detail["name"] == test_group.name
        assert log.detail["id"] == test_group.pk

    def test_non_existent(self, staff_client):
        resp = staff_client.delete(f"{URL}/groups/99999/")
        assert_not_found(resp)
        assert resp.json()["message"] == "小组不存在"


# ═══════════════════════════════════════════════════════════════
#  19. AdminGroupPostsView
# ═══════════════════════════════════════════════════════════════

class TestAdminGroupPostsView:
    def test_list(self, staff_client, test_group, group_post):
        data = assert_ok(staff_client.get(f"{URL}/groups/{test_group.pk}/posts/"))
        assert data["total"] >= 1
        assert data["results"][0]["content"] == "Group post"

    def test_response_shape(self, staff_client, test_group, group_post):
        data = assert_ok(staff_client.get(f"{URL}/groups/{test_group.pk}/posts/"))
        item = data["results"][0]
        for key in ("id", "author_name", "content", "created_at"):
            assert key in item

    def test_empty(self, staff_client, test_group):
        data = assert_ok(staff_client.get(f"{URL}/groups/{test_group.pk}/posts/"))
        assert data["total"] == 0

    def test_non_existent_group(self, staff_client):
        resp = staff_client.get(f"{URL}/groups/99999/posts/")
        assert_not_found(resp)
        assert resp.json()["message"] == "小组不存在"

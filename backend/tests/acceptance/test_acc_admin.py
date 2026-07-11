import pytest
from rest_framework import status

BASE = "/api/v1/admin/"

pytestmark = pytest.mark.django_db


class TestAccessControl:
    """Non-admin users must be blocked from every admin endpoint."""

    list_endpoints = [
        "users/", "posts/", "comments/", "settings/", "stats/",
        "logs/", "plugins/", "groups/", "anonymous-questions/",
        "quiz/questions/", "logs/actions/",
    ]

    detail_patch_endpoints = ["users/1/", "plugins/1/"]

    detail_delete_endpoints = ["posts/1/", "comments/1/", "groups/1/"]

    @pytest.mark.parametrize("path", list_endpoints)
    def test_non_admin_get_403(self, alice_client, path):
        resp = alice_client.get(BASE + path)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("path", detail_patch_endpoints)
    def test_non_admin_patch_403(self, alice_client, path):
        resp = alice_client.patch(BASE + path, {"is_active": False})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("path", detail_delete_endpoints)
    def test_non_admin_delete_403(self, alice_client, path):
        resp = alice_client.delete(BASE + path)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestUserList:
    def test_paginated(self, admin_client, alice, bob, charlie):
        resp = admin_client.get(BASE + "users/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["total"] >= 3
        assert data["page"] == 1
        assert data["page_size"] == 20
        user_ids = {u["id"] for u in data["results"]}
        assert alice.id in user_ids

    def test_search(self, admin_client, alice, bob):
        resp = admin_client.get(BASE + "users/", {"search": "ali"})
        assert resp.status_code == status.HTTP_200_OK
        ids = [u["id"] for u in resp.data["data"]["results"]]
        assert alice.id in ids
        assert bob.id not in ids


class TestUserToggleActive:
    """PATCH /admin/users/{id}/ — ban/activate (PRD §2.9)"""

    def test_toggle_active(self, admin_client, alice):
        resp = admin_client.patch(BASE + f"users/{alice.id}/", {"is_active": False})
        assert resp.status_code == status.HTTP_200_OK
        alice.refresh_from_db()
        assert alice.is_active is False

        resp = admin_client.patch(BASE + f"users/{alice.id}/", {"is_active": True})
        assert resp.status_code == status.HTTP_200_OK
        alice.refresh_from_db()
        assert alice.is_active is True


class TestPostListDelete:
    """GET/DELETE /admin/posts/ (PRD §2.9 内容管理)"""

    def test_list_paginated(self, admin_client, alice_post, bob_post):
        resp = admin_client.get(BASE + "posts/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["total"] >= 2
        assert len(data["results"]) >= 2

    def test_delete_post(self, admin_client, alice_post):
        resp = admin_client.delete(BASE + f"posts/{alice_post.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert not alice_post.__class__.objects.filter(id=alice_post.id).exists()


class TestCommentListAndDelete:
    """GET/DELETE /admin/comments/ (PRD §2.9 内容管理)"""

    def test_list_paginated(self, admin_client, alice_post, alice):
        from apps.feed.models import Comment
        Comment.objects.create(post=alice_post, author=alice, content="Test comment")

        resp = admin_client.get(BASE + "comments/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["total"] >= 1
        assert len(data["results"]) >= 1

    def test_delete_comment(self, admin_client, alice_post, alice):
        from apps.feed.models import Comment
        comment = Comment.objects.create(post=alice_post, author=alice, content="To delete")

        resp = admin_client.delete(BASE + f"comments/{comment.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert not Comment.objects.filter(id=comment.id).exists()


class TestStats:
    """GET /admin/stats/ (PRD §2.9 统计面板)"""

    def test_returns_all_fields(self, admin_client, alice_post, alice):
        from apps.feed.models import Comment
        Comment.objects.create(post=alice_post, author=alice, content="c")

        resp = admin_client.get(BASE + "stats/")
        assert resp.status_code == status.HTTP_200_OK
        stats = resp.data["data"]
        expected = {"total_users", "total_posts", "total_comments", "total_messages", "active_users_today"}
        assert expected == set(stats.keys())
        assert stats["total_users"] >= 1
        assert stats["total_posts"] >= 1
        assert stats["total_comments"] >= 1


class TestSettingsRoundTrip:
    """GET/PATCH /admin/settings/ (PRD §2.9 站点设置)"""

    def test_get_and_update_settings(self, admin_client):
        resp = admin_client.get(BASE + "settings/")
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data["data"], list)

        new_settings = {"site_name": "Test Haven", "allow_register": "false"}
        resp = admin_client.patch(BASE + "settings/", {"settings": new_settings}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        items = {s["key"]: s["value"] for s in resp.data["data"]}
        assert items["site_name"] == "Test Haven"
        assert items["allow_register"] == "false"


class TestPluginListAndToggle:
    """GET/PATCH /admin/plugins/ (PRD §2.9 插件管理)"""

    def test_list_plugins(self, admin_client):
        resp = admin_client.get(BASE + "plugins/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert "results" in data
        assert "total" in data

    def test_toggle_plugin(self, admin_client):
        from apps.plugins.models import Plugin
        plugin = Plugin.objects.create(name="Test", plugin_type="test", is_active=True)

        resp = admin_client.patch(BASE + f"plugins/{plugin.id}/", {"is_active": False})
        assert resp.status_code == status.HTTP_200_OK
        plugin.refresh_from_db()
        assert plugin.is_active is False

        resp = admin_client.patch(BASE + f"plugins/{plugin.id}/", {"is_active": True})
        assert resp.status_code == status.HTTP_200_OK
        plugin.refresh_from_db()
        assert plugin.is_active is True


class TestLogsList:
    """GET /admin/logs/ (PRD §2.9 操作日志)"""

    def test_list_logs(self, admin_client, admin_user, alice):
        from apps.admin_dashboard.models import SiteLog
        SiteLog.objects.create(user=admin_user, action="test_action", detail={"foo": "bar"})

        resp = admin_client.get(BASE + "logs/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["total"] >= 1
        assert len(data["results"]) >= 1

    def test_list_log_actions(self, admin_client, admin_user):
        from apps.admin_dashboard.models import SiteLog
        SiteLog.objects.create(user=admin_user, action="test_action", detail={})

        resp = admin_client.get(BASE + "logs/actions/")
        assert resp.status_code == status.HTTP_200_OK
        assert "test_action" in resp.data["data"]


class TestAnonymousQuestions:
    """GET /admin/anonymous-questions/ (PRD §2.9 查看匿名真实发送者)"""

    def test_list_anon_questions(self, admin_client, alice, bob):
        from apps.plugins.questions.models import AnonymousQuestion
        q = AnonymousQuestion.objects.create(recipient=alice, sender=bob, content="Anon Q?")
        resp = admin_client.get(BASE + "anonymous-questions/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["total"] >= 1
        ids = [r["id"] for r in data["results"]]
        assert q.id in ids


class TestQuizQuestions:
    """GET /admin/quiz/questions/"""

    def test_list_quiz_questions(self, admin_client, alice, bob):
        from apps.plugins.quizzes.models import QuizQuestion
        q = QuizQuestion.objects.create(creator=alice, target_user=bob, question="Like me?")
        resp = admin_client.get(BASE + "quiz/questions/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["total"] >= 1
        ids = [r["id"] for r in data["results"]]
        assert q.id in ids


class TestGroupListAndDelete:
    """GET/DELETE /admin/groups/ (PRD §2.9 小组管理)"""

    def test_list_groups(self, admin_client, test_group):
        resp = admin_client.get(BASE + "groups/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["total"] >= 1
        ids = [g["id"] for g in data["results"]]
        assert test_group.id in ids

    def test_delete_group(self, admin_client, test_group):
        resp = admin_client.delete(BASE + f"groups/{test_group.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert not test_group.__class__.objects.filter(id=test_group.id).exists()
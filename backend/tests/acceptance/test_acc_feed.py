import pytest
from rest_framework import status

BASE = "/api/v1/posts/"

pytestmark = pytest.mark.django_db


def _unwrap(resp):
    return resp.data.get("data", resp.data)


EXPECTED_POST_FIELDS = {
    "id", "content", "user", "created_at", "is_liked",
    "like_count", "comment_count", "image_urls", "files",
    "visibility", "group", "topic_tag",
}


def _assert_post_fields(data):
    missing = EXPECTED_POST_FIELDS - set(data.keys())
    if missing:
        pytest.fail(f"Missing expected post fields: {missing}")
    for field in ("user_id", "nickname", "username", "avatar_url"):
        assert field in data["user"], f"Missing user.{field}"


def _post_ids(resp):
    data = _unwrap(resp)
    if isinstance(data, list):
        return [p["id"] for p in data]
    return [p["id"] for p in data.get("results", [])]


class TestCreatePost:
    """PRD §2.3 — 用户可发布图文动态"""

    def test_create_public_post(self, alice_client):
        resp = alice_client.post(BASE + "create/", {
            "content": "Hello world", "visibility": "public",
        })
        assert resp.status_code == status.HTTP_201_CREATED
        data = _unwrap(resp)
        _assert_post_fields(data)
        assert data["content"] == "Hello world"
        assert data["visibility"] == "public"

    def test_create_post_requires_auth(self, client):
        resp = client.post(BASE + "create/", {"content": "Hacker"})
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_create_post_with_all_visibilities(self, alice_client):
        for vis in ("public", "friends", "private"):
            resp = alice_client.post(BASE + "create/", {
                "content": f"Test {vis}", "visibility": vis,
            })
            assert resp.status_code == status.HTTP_201_CREATED, f"Failed for {vis}"
            assert _unwrap(resp)["visibility"] == vis

    def test_empty_content_rejected(self, alice_client):
        resp = alice_client.post(BASE + "create/", {
            "content": "", "visibility": "public",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestPostVisibility:
    """PRD §2.3 — public 所有人, friends 仅好友, private 仅自己"""

    def test_public_visible_to_everyone(self, settings, alice_client, bob_client, public_post):
        settings.REST_FRAMEWORK = {"DEFAULT_THROTTLE_CLASSES": [], "DEFAULT_THROTTLE_RATES": {}}
        assert public_post.id in _post_ids(alice_client.get(BASE))
        assert public_post.id in _post_ids(bob_client.get(BASE))

    def test_friends_only_visible_to_friends(self, settings, alice_client, bob_client, charlie_client, friends_post, friendship):
        settings.REST_FRAMEWORK = {"DEFAULT_THROTTLE_CLASSES": [], "DEFAULT_THROTTLE_RATES": {}}
        assert friends_post.id in _post_ids(alice_client.get(BASE))
        assert friends_post.id in _post_ids(bob_client.get(BASE))
        assert friends_post.id not in _post_ids(charlie_client.get(BASE))

    def test_private_only_visible_to_author(self, settings, alice_client, bob_client):
        settings.REST_FRAMEWORK = {"DEFAULT_THROTTLE_CLASSES": [], "DEFAULT_THROTTLE_RATES": {}}
        resp = alice_client.post(BASE + "create/", {"content": "My secret", "visibility": "private"})
        post_id = _unwrap(resp)["id"]
        assert post_id in _post_ids(alice_client.get(BASE))
        assert post_id not in _post_ids(bob_client.get(BASE))


class TestPagination:
    """PRD §2.3 — 广场分页"""

    def _create_n_posts(self, client, n):
        for i in range(n):
            client.post(BASE + "create/", {
                "content": f"Post {i}", "visibility": "public",
            })

    def test_paginated_response_format(self, alice_client):
        self._create_n_posts(alice_client, 3)
        data = _unwrap(alice_client.get(BASE, {"page": 1, "page_size": 20}))
        assert "results" in data
        assert "page" in data
        assert "page_size" in data
        assert "total" in data

    def test_pagination_works(self, alice_client):
        self._create_n_posts(alice_client, 25)
        p1 = _unwrap(alice_client.get(BASE, {"page": 1, "page_size": 20}))
        assert len(p1["results"]) == 20
        assert p1["total"] >= 25
        p2 = _unwrap(alice_client.get(BASE, {"page": 2, "page_size": 20}))
        assert len(p2["results"]) >= 5


class TestLikePost:
    """PRD §2.3 — 点赞/取消点赞"""

    def test_like_toggles_state(self, bob_client, alice_post):
        resp = bob_client.post(BASE + f"{alice_post.id}/like/")
        assert resp.status_code == status.HTTP_200_OK
        data = _unwrap(resp)
        assert data["is_liked"] is True
        assert data["like_count"] == 1

        resp = bob_client.post(BASE + f"{alice_post.id}/like/")
        data = _unwrap(resp)
        assert data["is_liked"] is False
        assert data["like_count"] == 0

    def test_like_count_tracks_multiple(self, alice_client, bob_client, charlie_client, alice_post):
        bob_client.post(BASE + f"{alice_post.id}/like/")
        charlie_client.post(BASE + f"{alice_post.id}/like/")
        data = _unwrap(alice_client.get(BASE))
        post = next(p for p in data.get("results", []) if p["id"] == alice_post.id)
        assert post["like_count"] == 2

    def test_like_requires_auth(self, client, alice_post):
        resp = client.post(BASE + f"{alice_post.id}/like/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_like_nonexistent_post(self, bob_client):
        resp = bob_client.post(BASE + "99999/like/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestCommentOnPost:
    """PRD §2.3 — 评论"""

    def test_create_comment(self, bob_client, alice_post):
        resp = bob_client.post(BASE + f"{alice_post.id}/comments/create/", {
            "content": "Nice post!",
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert _unwrap(resp)["content"] == "Nice post!"

    def test_comment_updates_count(self, alice_client, bob_client, alice_post):
        bob_client.post(BASE + f"{alice_post.id}/comments/create/", {"content": "First"})
        bob_client.post(BASE + f"{alice_post.id}/comments/create/", {"content": "Second"})
        data = _unwrap(alice_client.get(BASE))
        post = next(p for p in data.get("results", []) if p["id"] == alice_post.id)
        assert post["comment_count"] == 2

    def test_comment_requires_auth(self, client, alice_post):
        resp = client.post(BASE + f"{alice_post.id}/comments/create/", {"content": "Hack"})
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_list_comments(self, bob_client, alice_post):
        bob_client.post(BASE + f"{alice_post.id}/comments/create/", {"content": "C1"})
        bob_client.post(BASE + f"{alice_post.id}/comments/create/", {"content": "C2"})
        resp = bob_client.get(BASE + f"{alice_post.id}/comments/")
        assert resp.status_code == status.HTTP_200_OK
        comments = _unwrap(resp)
        if isinstance(comments, dict):
            comments = comments.get("results", [])
        assert len(comments) == 2

    def test_delete_own_comment(self, bob_client, alice_post):
        resp = bob_client.post(BASE + f"{alice_post.id}/comments/create/", {"content": "To delete"})
        comment_id = _unwrap(resp)["id"]
        resp = bob_client.delete(BASE + f"comments/{comment_id}/delete/")
        assert resp.status_code == status.HTTP_200_OK

    def test_non_author_cannot_delete_own_comment_by_alice(self, bob_client, charlie_client, alice_post):
        """charlie (non-author, non-commenter) cannot delete bob's comment"""
        resp = bob_client.post(BASE + f"{alice_post.id}/comments/create/", {"content": "Bob's"})
        comment_id = _unwrap(resp)["id"]
        resp = charlie_client.delete(BASE + f"comments/{comment_id}/delete/")
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


class TestDeletePost:
    """PRD §2.3 — 删除动态"""

    def test_delete_own_post(self, alice_client, alice_post):
        resp = alice_client.delete(BASE + f"{alice_post.id}/delete/")
        assert resp.status_code == status.HTTP_200_OK

        resp = alice_client.get(BASE + f"{alice_post.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_other_post_rejected(self, bob_client, alice_post):
        resp = bob_client.delete(BASE + f"{alice_post.id}/delete/")
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_delete_post_requires_auth(self, client, alice_post):
        resp = client.delete(BASE + f"{alice_post.id}/delete/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_deleting_removes_from_feed(self, alice_client, alice_post):
        assert alice_post.id in _post_ids(alice_client.get(BASE))
        alice_client.delete(BASE + f"{alice_post.id}/delete/")
        assert alice_post.id not in _post_ids(alice_client.get(BASE))


class TestUploadImages:
    """PRD §2.3 — 图片上传"""

    def test_create_post_with_image(self, alice_client, fake_image):
        resp = alice_client.post(BASE + "create/", {
            "content": "With image", "visibility": "public",
            "images": [fake_image],
        }, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED
        assert len(_unwrap(resp)["image_urls"]) >= 1


class TestUiContract:
    """Consistent post shape across create/detail/list"""

    def test_post_detail_returns_expected_fields(self, alice_client, alice_post):
        _assert_post_fields(_unwrap(alice_client.get(BASE + f"{alice_post.id}/")))

    def test_list_paginated_with_expected_fields(self, alice_client, alice_post):
        data = _unwrap(alice_client.get(BASE))
        assert "results" in data
        assert "page" in data
        assert "page_size" in data
        assert "total" in data
        if data["results"]:
            _assert_post_fields(data["results"][0])

    def test_create_returns_single_post(self, alice_client):
        data = _unwrap(alice_client.post(BASE + "create/", {
            "content": "New post", "visibility": "public",
        }))
        _assert_post_fields(data)
        assert "results" not in data

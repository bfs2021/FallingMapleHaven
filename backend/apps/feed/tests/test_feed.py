import pytest
from rest_framework import status

from apps.feed.models import Comment, Like, Post

pytestmark = pytest.mark.django_db


# ── URL helpers ──────────────────────────────────────────────────────────────

POST_LIST_URL = "/api/v1/posts/"
POST_CREATE_URL = "/api/v1/posts/create/"


def post_url(pk):
    return f"/api/v1/posts/{pk}/"


def post_delete_url(pk):
    return f"/api/v1/posts/{pk}/delete/"


def post_like_url(pk):
    return f"/api/v1/posts/{pk}/like/"


def comment_list_url(pk):
    return f"/api/v1/posts/{pk}/comments/"


def comment_create_url(pk):
    return f"/api/v1/posts/{pk}/comments/create/"


def comment_delete_url(pk):
    return f"/api/v1/posts/comments/{pk}/delete/"


# ── PostListView ──────────────────────────────────────────────────────────────

class TestPostListView:

    def test_unauthenticated_sees_only_public_posts(self, client, alice_post, bob_post, public_post, friends_post):
        alice_post.visibility = Post.Visibility.PUBLIC
        alice_post.save()
        resp = client.get(POST_LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        ids = {p["id"] for p in resp.data["data"]["results"]}
        assert alice_post.id in ids
        assert bob_post.id in ids  # bob_post is public by default
        assert friends_post.id not in ids

    def test_authenticated_sees_own_posts_public_and_friends_posts(self, alice, bob, alice_client, bob_post, friends_post):
        Post.objects.create(author=alice, content="own-private", visibility=Post.Visibility.PRIVATE)
        resp = alice_client.get(POST_LIST_URL)
        ids = {p["id"] for p in resp.data["data"]["results"]}
        assert bob_post.id in ids  # bob's public post
        assert friends_post.id in ids  # alice is author of friends_post
        own_private = Post.objects.get(content="own-private")
        assert own_private.id in ids

    def test_sees_friends_friends_only_posts(self, alice, bob, alice_client, friendship):
        bob_friends = Post.objects.create(author=bob, content="bob-friends", visibility=Post.Visibility.FRIENDS)
        resp = alice_client.get(POST_LIST_URL)
        ids = {p["id"] for p in resp.data["data"]["results"]}
        assert bob_friends.id in ids

    def test_stranger_does_not_see_friends_only_post(self, charlie_client, friendship, friends_post):
        resp = charlie_client.get(POST_LIST_URL)
        ids = {p["id"] for p in resp.data["data"]["results"]}
        assert friends_post.id not in ids

    def test_filter_by_topic(self, alice_client, alice):
        Post.objects.create(author=alice, content="tech", topic_tag="tech")
        Post.objects.create(author=alice, content="art", topic_tag="art")
        resp = alice_client.get(POST_LIST_URL, {"topic": "tech"})
        contents = [p["content"] for p in resp.data["data"]["results"]]
        assert "tech" in contents
        assert "art" not in contents

    def test_empty_list_when_no_posts(self, alice_client):
        Post.objects.all().delete()
        resp = alice_client.get(POST_LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["results"] == []

    def test_response_includes_annotated_fields(self, alice_client, alice_post):
        resp = alice_client.get(POST_LIST_URL)
        post_data = next(p for p in resp.data["data"]["results"] if p["id"] == alice_post.id)
        assert "user" in post_data
        assert "comment_count" in post_data
        assert "like_count" in post_data
        assert "is_liked" in post_data
        assert "image_urls" in post_data

    def test_pagination(self, alice_client, alice):
        Post.objects.bulk_create([Post(author=alice, content=f"p{i}") for i in range(25)])
        resp = alice_client.get(POST_LIST_URL, {"page": 2})
        assert resp.data["data"]["page"] == 2
        assert resp.data["data"]["page_size"] == 20
        assert len(resp.data["data"]["results"]) == 5

    def test_group_posts_excluded_from_feed(self, alice_client, alice, test_group):
        Post.objects.create(author=alice, content="group-post", group=test_group)
        resp = alice_client.get(POST_LIST_URL)
        contents = [p["content"] for p in resp.data["data"]["results"]]
        assert "group-post" not in contents


# ── PostCreateView ────────────────────────────────────────────────────────────

class TestPostCreateView:

    def test_create_with_content_only(self, alice_client):
        resp = alice_client.post(POST_CREATE_URL, {"content": "Hello"})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["content"] == "Hello"
        assert resp.data["data"]["visibility"] == Post.Visibility.PUBLIC

    def test_create_with_visibility_friends(self, alice_client):
        resp = alice_client.post(POST_CREATE_URL, {"content": "Hello", "visibility": "friends"})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["visibility"] == "friends"

    def test_create_with_visibility_private(self, alice_client):
        resp = alice_client.post(POST_CREATE_URL, {"content": "Hello", "visibility": "private"})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["visibility"] == "private"

    def test_create_with_topic_tag(self, alice_client):
        resp = alice_client.post(POST_CREATE_URL, {"content": "Tech post", "topic_tag": "tech"})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["topic_tag"] == "tech"

    def test_create_post_to_group_as_member(self, alice_client, alice, test_group):
        resp = alice_client.post(POST_CREATE_URL, {"content": "Group post", "group_id": test_group.id})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["group_id"] == test_group.id

    def test_non_member_cannot_post_to_group(self, bob, bob_client, test_group):
        resp = bob_client.post(POST_CREATE_URL, {"content": "Hack", "group_id": test_group.id})
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["code"] == 40003

    def test_create_to_nonexistent_group_returns_404(self, alice_client):
        resp = alice_client.post(POST_CREATE_URL, {"content": "Bad", "group_id": 99999})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["code"] == 40004

    def test_missing_content_returns_error(self, alice_client):
        resp = alice_client.post(POST_CREATE_URL, {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_403(self, client):
        resp = client.post(POST_CREATE_URL, {"content": "Hello"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_too_many_images_returns_error(self, alice_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        import io
        from PIL import Image
        images = []
        for i in range(10):
            buf = io.BytesIO()
            Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
            buf.seek(0)
            images.append(SimpleUploadedFile(f"img{i}.jpg", buf.read(), content_type="image/jpeg"))
        resp = alice_client.post(POST_CREATE_URL, {"content": "Img", "images": images}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001

    def test_create_with_unsupported_image_extension(self, alice_client, fake_image):
        fake_image.name = "test.bmp"
        resp = alice_client.post(POST_CREATE_URL, {"content": "Bad img", "images": [fake_image]}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001

    def test_create_with_unsupported_file_extension(self, alice_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        bad_file = SimpleUploadedFile("test.exe", b"x" * 100)
        resp = alice_client.post(POST_CREATE_URL, {"content": "Bad file", "files": [bad_file]}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001

    def test_create_with_oversized_file(self, alice_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        big_file = SimpleUploadedFile("test.pdf", b"x" * (51 * 1024 * 1024))
        resp = alice_client.post(POST_CREATE_URL, {"content": "Big file", "files": [big_file]}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001


# ── PostDetailView ────────────────────────────────────────────────────────────

class TestPostDetailView:

    def test_own_post_any_visibility(self, alice_client, alice):
        post = Post.objects.create(author=alice, content="Secret", visibility=Post.Visibility.PRIVATE)
        resp = alice_client.get(post_url(post.id))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["content"] == "Secret"

    def test_friend_sees_friends_only_post(self, bob_client, friendship, friends_post):
        resp = bob_client.get(post_url(friends_post.id))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["content"] == friends_post.content

    def test_stranger_cannot_see_friends_only_post(self, charlie_client, friends_post):
        resp = charlie_client.get(post_url(friends_post.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["code"] == 40003

    def test_stranger_cannot_see_private_post(self, bob_client, alice):
        private = Post.objects.create(author=alice, content="Alone", visibility=Post.Visibility.PRIVATE)
        resp = bob_client.get(post_url(private.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_nonexistent_post_returns_404(self, alice_client):
        resp = alice_client.get(post_url(99999))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["code"] == 40004

    def test_unauthenticated_only_public(self, client, alice):
        public = Post.objects.create(author=alice, content="Pub", visibility=Post.Visibility.PUBLIC)
        private = Post.objects.create(author=alice, content="Priv", visibility=Post.Visibility.PRIVATE)
        resp_pub = client.get(post_url(public.id))
        assert resp_pub.status_code == status.HTTP_200_OK
        resp_priv = client.get(post_url(private.id))
        assert resp_priv.status_code == status.HTTP_403_FORBIDDEN

    def test_private_group_post_hidden_from_non_member(self, charlie_client, bob, private_group):
        post = Post.objects.create(author=bob, content="Private group", group=private_group)
        resp = charlie_client.get(post_url(post.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["code"] == 40003


# ── PostDeleteView ────────────────────────────────────────────────────────────

class TestPostDeleteView:

    def test_author_can_delete_own_post(self, alice_client, alice_post):
        resp = alice_client.delete(post_delete_url(alice_post.id))
        assert resp.status_code == status.HTTP_200_OK
        assert not Post.objects.filter(id=alice_post.id).exists()

    def test_staff_can_delete_any_post(self, staff_client, alice_post):
        resp = staff_client.delete(post_delete_url(alice_post.id))
        assert resp.status_code == status.HTTP_200_OK
        assert not Post.objects.filter(id=alice_post.id).exists()

    def test_other_user_cannot_delete(self, bob_client, alice_post):
        resp = bob_client.delete(post_delete_url(alice_post.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["code"] == 40003
        assert Post.objects.filter(id=alice_post.id).exists()

    def test_nonexistent_post_returns_404(self, alice_client):
        resp = alice_client.delete(post_delete_url(99999))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_403(self, client, alice_post):
        resp = client.delete(post_delete_url(alice_post.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── LikeView ──────────────────────────────────────────────────────────────────

class TestLikeView:

    def test_like_toggle_on(self, bob_client, alice_post):
        resp = bob_client.post(post_like_url(alice_post.id))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["is_liked"] is True
        assert resp.data["data"]["like_count"] == 1

    def test_like_toggle_off(self, bob_client, alice_post):
        Like.objects.create(post=alice_post, user=bob_client.handler._force_user)
        resp = bob_client.post(post_like_url(alice_post.id))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["is_liked"] is False
        assert resp.data["data"]["like_count"] == 0

    def test_like_own_post(self, alice_client, alice_post):
        resp = alice_client.post(post_like_url(alice_post.id))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["is_liked"] is True

    def test_like_nonexistent_post_returns_404(self, alice_client):
        resp = alice_client.post(post_like_url(99999))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["code"] == 40004

    def test_unauthenticated_returns_403(self, client, alice_post):
        resp = client.post(post_like_url(alice_post.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── CommentListView ───────────────────────────────────────────────────────────

class TestCommentListView:

    def test_returns_comments_with_author_info(self, alice_client, alice_post, bob):
        Comment.objects.create(post=alice_post, author=bob, content="Nice!")
        resp = alice_client.get(comment_list_url(alice_post.id))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1
        assert resp.data["data"][0]["content"] == "Nice!"
        assert "user" in resp.data["data"][0]

    def test_empty_when_no_comments(self, alice_client, alice_post):
        resp = alice_client.get(comment_list_url(alice_post.id))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"] == []

    def test_only_top_level_comments(self, alice_client, alice_post, bob):
        parent = Comment.objects.create(post=alice_post, author=bob, content="Parent")
        Comment.objects.create(post=alice_post, author=bob, content="Reply", parent=parent)
        resp = alice_client.get(comment_list_url(alice_post.id))
        assert len(resp.data["data"]) == 1
        assert resp.data["data"][0]["content"] == "Parent"

    def test_nonexistent_post_returns_404(self, alice_client):
        resp = alice_client.get(comment_list_url(99999))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["code"] == 40004

    def test_unauthenticated_can_see_public_post_comments(self, client, alice_post, bob):
        Comment.objects.create(post=alice_post, author=bob, content="Public")
        resp = client.get(comment_list_url(alice_post.id))
        assert resp.status_code == status.HTTP_200_OK


# ── CommentCreateView ─────────────────────────────────────────────────────────

class TestCommentCreateView:

    def test_create_comment_on_visible_post(self, bob_client, alice_post):
        resp = bob_client.post(comment_create_url(alice_post.id), {"content": "Great!"})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["content"] == "Great!"
        assert Comment.objects.filter(post=alice_post, content="Great!").exists()

    def test_reply_to_existing_comment(self, bob_client, alice_post):
        parent = Comment.objects.create(post=alice_post, author=bob_client.handler._force_user, content="Parent")
        resp = bob_client.post(comment_create_url(alice_post.id), {"content": "Reply", "parent": parent.id})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["parent"] == parent.id

    def test_reply_to_nonexistent_parent_returns_404(self, bob_client, alice_post):
        resp = bob_client.post(comment_create_url(alice_post.id), {"content": "Reply", "parent": 99999})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["code"] == 40004

    def test_missing_content_returns_error(self, bob_client, alice_post):
        resp = bob_client.post(comment_create_url(alice_post.id), {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_comment_on_nonexistent_post_returns_404(self, bob_client):
        resp = bob_client.post(comment_create_url(99999), {"content": "Hello"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["code"] == 40004

    def test_unauthenticated_returns_403(self, client, alice_post):
        resp = client.post(comment_create_url(alice_post.id), {"content": "Hello"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ── CommentDeleteView ─────────────────────────────────────────────────────────

class TestCommentDeleteView:

    def test_comment_author_can_delete(self, bob_client, alice_post, bob):
        comment = Comment.objects.create(post=alice_post, author=bob, content="Mine")
        resp = bob_client.delete(comment_delete_url(comment.id))
        assert resp.status_code == status.HTTP_200_OK
        assert not Comment.objects.filter(id=comment.id).exists()

    def test_post_author_can_delete_any_comment(self, alice_client, alice_post, bob):
        comment = Comment.objects.create(post=alice_post, author=bob, content="By bob")
        resp = alice_client.delete(comment_delete_url(comment.id))
        assert resp.status_code == status.HTTP_200_OK
        assert not Comment.objects.filter(id=comment.id).exists()

    def test_staff_can_delete_any_comment(self, staff_client, alice_post, bob):
        comment = Comment.objects.create(post=alice_post, author=bob, content="By bob")
        resp = staff_client.delete(comment_delete_url(comment.id))
        assert resp.status_code == status.HTTP_200_OK
        assert not Comment.objects.filter(id=comment.id).exists()

    def test_other_user_cannot_delete(self, charlie_client, alice_post, bob):
        comment = Comment.objects.create(post=alice_post, author=bob, content="By bob")
        resp = charlie_client.delete(comment_delete_url(comment.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["code"] == 40003
        assert Comment.objects.filter(id=comment.id).exists()

    def test_nonexistent_comment_returns_404(self, alice_client):
        resp = alice_client.delete(comment_delete_url(99999))
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["code"] == 40004

    def test_unauthenticated_returns_403(self, client, alice_post, bob):
        comment = Comment.objects.create(post=alice_post, author=bob, content="By bob")
        resp = client.delete(comment_delete_url(comment.id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

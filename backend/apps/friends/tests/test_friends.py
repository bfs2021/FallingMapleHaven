import pytest
from rest_framework import status

from apps.friends.models import Friendship

BASE = "/api/v1/friends/"
FRIEND_REQUEST_URL = BASE + "request/"
FRIEND_HANDLE_URL = BASE + "handle/"
UNFRIEND_URL = BASE + "unfriend/"
FRIEND_LIST_URL = BASE
FRIEND_REQUESTS_URL = BASE + "requests/"
FRIEND_SEARCH_URL = BASE + "search/"


# ═══════════════════════════════════════════════════════════════
# FriendRequestView  —  POST /api/v1/friends/request/
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestFriendRequestView:
    def test_send_request_success(self, charlie_client, charlie, bob):
        resp = charlie_client.post(FRIEND_REQUEST_URL, {"to_user_id": bob.id})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["code"] == 0
        assert resp.data["message"] == "好友申请已发送"
        assert Friendship.objects.filter(
            from_user=charlie, to_user=bob, status=Friendship.Status.PENDING
        ).exists()

    def test_send_request_to_existing_friend(self, alice_client, bob, friendship):
        resp = alice_client.post(FRIEND_REQUEST_URL, {"to_user_id": bob.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert resp.data["message"] == "已是好友"

    def test_duplicate_request_returns_error(self, bob_client, charlie):
        bob_client.post(FRIEND_REQUEST_URL, {"to_user_id": charlie.id})
        resp = bob_client.post(FRIEND_REQUEST_URL, {"to_user_id": charlie.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert "已发送" in resp.data["message"]

    def test_send_request_to_self(self, alice_client, alice):
        resp = alice_client.post(FRIEND_REQUEST_URL, {"to_user_id": alice.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert resp.data["message"] == "不能添加自己为好友"

    def test_send_request_to_nonexistent_user(self, alice_client):
        resp = alice_client.post(FRIEND_REQUEST_URL, {"to_user_id": 99999})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["code"] == 40004
        assert resp.data["message"] == "用户不存在"

    def test_unauthenticated_returns_403(self, client, bob):
        resp = client.post(FRIEND_REQUEST_URL, {"to_user_id": bob.id})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_concurrent_duplicate_no_integrity_error(self, bob_client, charlie):
        bob_client.post(FRIEND_REQUEST_URL, {"to_user_id": charlie.id})
        resp = bob_client.post(FRIEND_REQUEST_URL, {"to_user_id": charlie.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ═══════════════════════════════════════════════════════════════
# FriendHandleView  —  POST /api/v1/friends/handle/
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestFriendHandleView:
    def test_accept_via_from_user_id(self, alice_client, bob, pending_friend_request):
        resp = alice_client.post(FRIEND_HANDLE_URL, {
            "from_user_id": bob.id, "action": "accept"
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["code"] == 0
        assert resp.data["message"] == "好友请求已接受"
        pending_friend_request.refresh_from_db()
        assert pending_friend_request.status == Friendship.Status.ACCEPTED

    def test_accept_via_request_id(self, alice_client, pending_friend_request):
        resp = alice_client.post(FRIEND_HANDLE_URL, {
            "request_id": pending_friend_request.id, "action": "accept"
        })
        assert resp.status_code == status.HTTP_200_OK
        pending_friend_request.refresh_from_db()
        assert pending_friend_request.status == Friendship.Status.ACCEPTED

    def test_reject_pending_request(self, alice_client, bob, pending_friend_request):
        resp = alice_client.post(FRIEND_HANDLE_URL, {
            "from_user_id": bob.id, "action": "reject"
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["message"] == "好友请求已拒绝"
        pending_friend_request.refresh_from_db()
        assert pending_friend_request.status == Friendship.Status.REJECTED

    def test_handle_nonexistent_request_id(self, alice_client):
        resp = alice_client.post(FRIEND_HANDLE_URL, {
            "request_id": 99999, "action": "accept"
        })
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["code"] == 40004

    def test_handle_already_handled_request(self, alice_client, bob, pending_friend_request):
        alice_client.post(FRIEND_HANDLE_URL, {"from_user_id": bob.id, "action": "accept"})
        resp = alice_client.post(FRIEND_HANDLE_URL, {"from_user_id": bob.id, "action": "accept"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["code"] == 40004

    def test_non_receiver_cannot_handle(self, charlie_client, bob, pending_friend_request):
        resp = charlie_client.post(FRIEND_HANDLE_URL, {
            "from_user_id": bob.id, "action": "accept"
        })
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["code"] == 40004

    def test_missing_both_ids_returns_error(self, alice_client):
        resp = alice_client.post(FRIEND_HANDLE_URL, {"action": "accept"})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert resp.data["message"] == "缺少请求参数"

    def test_unauthenticated_returns_403(self, client, bob):
        resp = client.post(FRIEND_HANDLE_URL, {"from_user_id": bob.id, "action": "accept"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════════════════════
# UnfriendView  —  POST /api/v1/friends/unfriend/
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestUnfriendView:
    def test_unfriend_existing_friend(self, alice_client, bob, friendship):
        resp = alice_client.post(UNFRIEND_URL, {"friend_id": bob.id})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["code"] == 0
        assert resp.data["message"] == "已解除好友关系"
        assert not Friendship.objects.filter(id=friendship.id).exists()

    def test_unfriend_non_friend(self, alice_client, charlie):
        resp = alice_client.post(UNFRIEND_URL, {"friend_id": charlie.id})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["code"] == 40004
        assert resp.data["message"] == "好友关系不存在"

    def test_unfriend_self(self, alice_client, alice):
        resp = alice_client.post(UNFRIEND_URL, {"friend_id": alice.id})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["code"] == 40004

    def test_unauthenticated_returns_403(self, client, bob):
        resp = client.post(UNFRIEND_URL, {"friend_id": bob.id})
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════════════════════
# FriendListView  —  GET /api/v1/friends/
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestFriendListView:
    def test_list_accepted_friends(self, alice_client, bob, friendship):
        resp = alice_client.get(FRIEND_LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["code"] == 0
        assert len(resp.data["data"]) == 1
        friend = resp.data["data"][0]
        assert friend["id"] == bob.id
        assert friend["nickname"] == bob.nickname

    def test_friend_response_contains_required_fields(self, alice_client, bob, friendship):
        resp = alice_client.get(FRIEND_LIST_URL)
        friend = resp.data["data"][0]
        assert "id" in friend
        assert "nickname" in friend
        assert "avatar_url" in friend
        assert "created_at" in friend

    def test_empty_when_no_friends(self, charlie_client):
        resp = charlie_client.get(FRIEND_LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"] == []

    def test_does_not_return_pending_requests(self, alice_client, pending_friend_request):
        resp = alice_client.get(FRIEND_LIST_URL)
        assert resp.data["data"] == []

    def test_unauthenticated_returns_403(self, client):
        resp = client.get(FRIEND_LIST_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════════════════════
# FriendRequestReceivedView  —  GET /api/v1/friends/requests/
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestFriendRequestReceivedView:
    def test_list_pending_requests(self, alice_client, bob, pending_friend_request):
        resp = alice_client.get(FRIEND_REQUESTS_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["code"] == 0
        assert len(resp.data["data"]) == 1
        req = resp.data["data"][0]
        assert req["from_user"]["user_id"] == bob.id
        assert req["from_user"]["nickname"] == bob.nickname

    def test_response_contains_required_fields(self, alice_client, pending_friend_request):
        resp = alice_client.get(FRIEND_REQUESTS_URL)
        req = resp.data["data"][0]
        assert "id" in req
        assert "nickname" in req
        assert "from_user" in req
        assert "created_at" in req
        assert "user_id" in req["from_user"]
        assert "nickname" in req["from_user"]
        assert "avatar_url" in req["from_user"]

    def test_empty_when_no_pending_requests(self, bob_client):
        resp = bob_client.get(FRIEND_REQUESTS_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"] == []

    def test_unauthenticated_returns_403(self, client):
        resp = client.get(FRIEND_REQUESTS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════════════════════
# UserSearchView  —  GET /api/v1/friends/search/?q=xxx
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestUserSearchView:
    def test_search_by_username_partial(self, alice_client, bob):
        resp = alice_client.get(FRIEND_SEARCH_URL, {"q": "bo"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["code"] == 0
        assert len(resp.data["data"]) == 1
        assert resp.data["data"][0]["id"] == bob.id
        assert resp.data["data"][0]["username"] == bob.username

    def test_search_by_nickname_partial(self, alice_client, charlie):
        resp = alice_client.get(FRIEND_SEARCH_URL, {"q": "Charl"})
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["data"]) == 1
        assert resp.data["data"][0]["id"] == charlie.id
        assert resp.data["data"][0]["nickname"] == charlie.nickname

    def test_no_results_for_non_matching_query(self, alice_client):
        resp = alice_client.get(FRIEND_SEARCH_URL, {"q": "zzzxxx"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"] == []

    def test_empty_query_returns_empty_list(self, alice_client):
        resp = alice_client.get(FRIEND_SEARCH_URL, {"q": ""})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"] == []

    def test_does_not_return_searcher(self, alice_client, alice):
        resp = alice_client.get(FRIEND_SEARCH_URL, {"q": "ali"})
        assert resp.status_code == status.HTTP_200_OK
        for user in resp.data["data"]:
            assert user["id"] != alice.id

    def test_unauthenticated_returns_403(self, client):
        resp = client.get(FRIEND_SEARCH_URL, {"q": "bob"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

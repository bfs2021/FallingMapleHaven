import pytest
from rest_framework import status

BASE = "/api/v1/friends/"

pytestmark = pytest.mark.django_db


def _friend_ids(resp):
    return [item["id"] for item in resp.data.get("data", [])]


class TestSendFriendRequest:
    """POST /friends/request/ — PRD §2.2"""

    def test_send_request_success(self, charlie_client, alice):
        resp = charlie_client.post(BASE + "request/", {"to_user_id": alice.id})
        assert resp.status_code == status.HTTP_201_CREATED

    def test_cannot_friend_self(self, alice_client, alice):
        resp = alice_client.post(BASE + "request/", {"to_user_id": alice.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_send_duplicate_request(self, charlie_client, alice):
        charlie_client.post(BASE + "request/", {"to_user_id": alice.id})
        resp = charlie_client.post(BASE + "request/", {"to_user_id": alice.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_request_existing_friend(self, alice_client, bob, friendship):
        resp = alice_client.post(BASE + "request/", {"to_user_id": bob.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_requires_auth(self, client, alice):
        resp = client.post(BASE + "request/", {"to_user_id": alice.id})
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestAcceptFriendRequest:
    """POST /friends/handle/ action=accept — PRD §2.2"""

    def _get_first_pending_id(self, client):
        resp = client.get(BASE + "requests/")
        data = resp.data.get("data", [])
        return data[0]["id"] if data else None

    def test_accept_request(self, alice_client, charlie_client, alice, charlie):
        charlie_client.post(BASE + "request/", {"to_user_id": alice.id})
        request_id = self._get_first_pending_id(alice_client)
        assert request_id is not None

        resp = alice_client.post(BASE + "handle/",
                                 {"request_id": request_id, "action": "accept"})
        assert resp.status_code == status.HTTP_200_OK

        assert charlie.id in _friend_ids(alice_client.get(BASE))

    def test_accept_requires_auth(self, client):
        resp = client.post(BASE + "handle/", {"request_id": 1, "action": "accept"})
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestRejectFriendRequest:
    """POST /friends/handle/ action=reject — PRD §2.2"""

    def _get_first_pending_id(self, client):
        resp = client.get(BASE + "requests/")
        data = resp.data.get("data", [])
        return data[0]["id"] if data else None

    def test_reject_request(self, alice_client, charlie_client, alice):
        charlie_client.post(BASE + "request/", {"to_user_id": alice.id})
        request_id = self._get_first_pending_id(alice_client)
        assert request_id is not None

        resp = alice_client.post(BASE + "handle/",
                                 {"request_id": request_id, "action": "reject"})
        assert resp.status_code == status.HTTP_200_OK

        remaining = [r["id"] for r in
                     alice_client.get(BASE + "requests/").data.get("data", [])]
        assert request_id not in remaining

    def test_reject_nonexistent_request(self, alice_client):
        resp = alice_client.post(BASE + "handle/",
                                 {"request_id": 99999, "action": "reject"})
        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND)


class TestFriendList:
    """GET /friends/ — PRD §2.2"""

    def test_list_accepted_friends(self, alice_client, bob, friendship):
        assert bob.id in _friend_ids(alice_client.get(BASE))

    def test_list_empty_for_new_user(self, charlie_client):
        assert len(charlie_client.get(BASE).data.get("data", [])) == 0

    def test_requires_auth(self, client):
        resp = client.get(BASE)
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestPendingRequests:
    """GET /friends/requests/ — PRD §2.2"""

    def test_list_pending_requests(self, alice_client, pending_friend_request, bob):
        data = alice_client.get(BASE + "requests/").data.get("data", [])
        from_ids = [r["from_user"]["user_id"] for r in data]
        assert bob.id in from_ids

    def test_pending_request_fields(self, alice_client, pending_friend_request, bob):
        data = alice_client.get(BASE + "requests/").data.get("data", [])
        for req in data:
            if req["from_user"]["user_id"] == bob.id:
                assert "id" in req
                assert req["from_user"]["user_id"] == bob.id
                assert req["from_user"]["nickname"] == bob.nickname
                break
        else:
            pytest.fail("Pending request from bob not found")

    def test_requires_auth(self, client):
        resp = client.get(BASE + "requests/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestUnfriend:
    """POST /friends/unfriend/ — PRD §2.2"""

    def test_unfriend_success(self, alice_client, bob, friendship):
        resp = alice_client.post(BASE + "unfriend/", {"friend_id": bob.id})
        assert resp.status_code == status.HTTP_200_OK
        assert bob.id not in _friend_ids(alice_client.get(BASE))

    def test_unfriend_requires_existing_friend(self, alice_client, charlie):
        resp = alice_client.post(BASE + "unfriend/", {"friend_id": charlie.id})
        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND)

    def test_unfriend_is_one_sided(self, alice_client, bob_client, bob, alice, friendship):
        alice_client.post(BASE + "unfriend/", {"friend_id": bob.id})
        assert alice.id not in _friend_ids(bob_client.get(BASE))

    def test_unfriend_requires_auth(self, client, bob):
        resp = client.post(BASE + "unfriend/", {"friend_id": bob.id})
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestSearchUsers:
    """GET /friends/search/ — PRD §2.2"""

    def _search_ids(self, client, q):
        data = client.get(BASE + "search/", {"q": q}).data.get("data", [])
        return [u["id"] for u in data]

    def test_search_by_username(self, alice_client, bob):
        assert bob.id in self._search_ids(alice_client, bob.username[:2])

    def test_search_by_nickname(self, alice_client, charlie):
        assert charlie.id in self._search_ids(alice_client, charlie.nickname[:3])

    def test_search_no_results(self, alice_client):
        assert self._search_ids(alice_client, "zzzznonexistent") == []

    def test_search_excludes_self(self, alice_client, alice):
        assert alice.id not in self._search_ids(alice_client, alice.username)

    def test_search_requires_auth(self, client, alice):
        resp = client.get(BASE + "search/", {"q": alice.username})
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestAlreadyFriendsStatus:
    """PRD §2.2 — friends not in pending list, can't re-request"""

    def test_friends_not_in_pending(self, alice_client, bob, friendship):
        assert bob.id in _friend_ids(alice_client.get(BASE))
        for req in alice_client.get(BASE + "requests/").data.get("data", []):
            assert req["from_user"]["user_id"] != bob.id

    def test_cannot_send_request_to_friend(self, alice_client, bob, friendship):
        resp = alice_client.post(BASE + "request/", {"to_user_id": bob.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

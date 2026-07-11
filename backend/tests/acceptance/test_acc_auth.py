import pytest
from rest_framework import status

BASE = "/api/v1/auth/"

pytestmark = pytest.mark.django_db


def _assert_user_fields(data):
    """Frontend expects these fields in user objects from register/login/me."""
    expected = {
        "user_id", "username", "nickname", "avatar_url", "cover_url",
        "bio", "email", "real_name", "show_real_name", "visitor_public",
        "date_joined", "is_admin", "unread_count",
    }
    missing = expected - set(data.keys())
    if missing:
        pytest.fail(f"Missing expected user fields: {missing}")


class TestRegisterLoginFlow:
    """Register -> auto-login -> me -> logout (PRD §2.1/§4 用户故事1)"""

    def test_full_register_login_logout_flow(self, client):
        resp = client.post(BASE + "register/", {
            "username": "freshuser",
            "nickname": "Newcomer",
            "password": "Pass1234!",
            "email": "new@example.com",
        })
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.data.get("data")
        assert data is not None
        _assert_user_fields(data)
        assert data["username"] == "freshuser"
        assert data["nickname"] == "Newcomer"
        user_id = data["user_id"]

        resp = client.get(BASE + "me/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["user_id"] == user_id

        resp = client.post(BASE + "logout/")
        assert resp.status_code == status.HTTP_200_OK

        resp = client.get(BASE + "me/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_register_with_duplicate_username(self, client, alice):
        resp = client.post(BASE + "register/", {
            "username": alice.username,
            "nickname": "Trying",
            "password": "Pass1234!",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data.get("code") is not None

    def test_register_with_weak_password(self, client):
        resp = client.post(BASE + "register/", {
            "username": "weakpwd",
            "nickname": "Weak",
            "password": "short",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_without_special_char(self, client):
        resp = client.post(BASE + "register/", {
            "username": "nospecial",
            "nickname": "NoSpec",
            "password": "Password1",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_success(self, client, alice):
        resp = client.post(BASE + "login/", {
            "username": alice.username,
            "password": "Pass1234!",
        })
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data.get("data")
        assert data is not None
        _assert_user_fields(data)
        assert data["user_id"] == alice.id

    def test_login_wrong_password(self, client, alice):
        resp = client.post(BASE + "login/", {
            "username": alice.username,
            "password": "WrongPass1!",
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, client):
        resp = client.post(BASE + "login/", {
            "username": "nobody",
            "password": "Pass1234!",
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestMeAndUpdate:
    """GET/PATCH /me/ (PRD §2.1 用户可修改个人信息)"""

    def test_me_returns_authenticated_user(self, alice_client, alice):
        resp = alice_client.get(BASE + "me/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        _assert_user_fields(data)
        assert data["user_id"] == alice.id

    def test_me_requires_auth(self, client):
        resp = client.get(BASE + "me/")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_update_nickname_and_bio(self, alice_client):
        resp = alice_client.patch(BASE + "me/", {
            "nickname": "NewNick",
            "bio": "Updated bio text",
        })
        assert resp.status_code == status.HTTP_200_OK
        data = resp.data["data"]
        assert data["nickname"] == "NewNick"
        assert data["bio"] == "Updated bio text"

    def test_update_visibility_settings(self, alice_client):
        resp = alice_client.patch(BASE + "me/", {
            "show_real_name": True,
            "visitor_public": False,
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["show_real_name"] is True
        assert resp.data["data"]["visitor_public"] is False

    def test_update_permanent_fields_require_auth(self, client, alice):
        resp = client.patch(BASE + "me/", {"nickname": "Hacker"})
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestChangePassword:
    """POST /change-password/ (PRD §2.1)"""

    def test_successful_password_change(self, client, alice):
        client.force_authenticate(alice)
        resp = client.post(BASE + "change-password/", {
            "old_password": "Pass1234!",
            "new_password": "NewPass789!",
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["code"] == 0

        client.logout()
        resp = client.post(BASE + "login/", {
            "username": alice.username,
            "password": "NewPass789!",
        })
        assert resp.status_code == status.HTTP_200_OK

    def test_wrong_old_password(self, alice_client):
        resp = alice_client.post(BASE + "change-password/", {
            "old_password": "WrongOld1!",
            "new_password": "NewPass789!",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_weak_new_password(self, alice_client):
        resp = alice_client.post(BASE + "change-password/", {
            "old_password": "Pass1234!",
            "new_password": "weak",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestAvatarCoverUpload:
    """POST /avatar/ and /cover/ (PRD §2.1)"""

    def test_upload_avatar(self, alice_client, fake_image):
        resp = alice_client.post(BASE + "avatar/", {"avatar": fake_image}, format="multipart")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["avatar_url"] is not None

    def test_upload_cover(self, alice_client, fake_image):
        resp = alice_client.post(BASE + "cover/", {"cover_image": fake_image}, format="multipart")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["cover_url"] is not None

    def test_avatar_rejects_non_image(self, alice_client):
        resp = alice_client.post(BASE + "avatar/", {
            "avatar": b"not an image",
        }, format="multipart", HTTP_CONTENT_DISPOSITION="attachment; filename=test.txt")
        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_upload_avatar_requires_auth(self, client, fake_image):
        resp = client.post(BASE + "avatar/", {"avatar": fake_image}, format="multipart")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


class TestCsrf:
    """GET /csrf/ (frontend interceptor dependency)"""

    def test_get_csrf_token(self, client):
        resp = client.get(BASE + "csrf/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["data"]["csrfToken"] is not None


class TestRegistrationUiContract:
    """Frontend expects register+login+me to return same shape (PRD §2)"""

    REGISTER_FIELDS = {
        "user_id", "username", "nickname", "avatar_url", "cover_url",
        "bio", "email", "real_name", "show_real_name", "visitor_public",
        "date_joined", "is_admin", "unread_count",
    }

    def test_register_returns_all_frontend_fields(self, client):
        resp = client.post(BASE + "register/", {
            "username": "contract_user",
            "nickname": "Contract",
            "password": "Pass1234!",
        })
        assert resp.status_code == status.HTTP_201_CREATED
        keys = set(resp.data["data"].keys())
        missing = self.REGISTER_FIELDS - keys
        extra = keys - self.REGISTER_FIELDS
        if missing:
            pytest.fail(f"Missing fields in register response: {missing}")
        if extra:
            pytest.fail(f"Unexpected extra fields in register response: {extra}")

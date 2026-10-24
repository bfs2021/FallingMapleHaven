import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from apps.accounts.models import User
from apps.profiles.models import UserProfile

User = get_user_model()

BASE = "/api/v1/auth/"


# ── Helpers ─────────────────────────────────────────────────────

def _non_image_file():
    return SimpleUploadedFile("test.txt", b"not an image", content_type="text/plain")


# ── CsrfTokenView ──────────────────────────────────────────────

@pytest.mark.django_db
class TestCsrfTokenView:
    def test_returns_csrf_token(self, client):
        resp = client.get(BASE + "csrf/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["code"] == 0
        assert "csrfToken" in resp.data["data"]


# ── RegisterView ───────────────────────────────────────────────

@pytest.mark.django_db
class TestRegisterView:
    def test_success_returns_201_with_full_profile(self, client):
        payload = {
            "username": "newuser",
            "password": "ValidPass1!",
            "nickname": "New User",
            "email": "new@example.com",
        }
        resp = client.post(BASE + "register/", payload)
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["code"] == 0
        d = resp.data["data"]
        assert d["user_id"] is not None
        assert d["username"] == "newuser"
        assert d["nickname"] == "New User"
        assert d["email"] == "new@example.com"
        assert d["bio"] is None
        assert d["avatar_url"] is None
        assert d["cover_url"] is None
        assert d["show_real_name"] is False
        assert d["visitor_public"] is True
        assert d["is_admin"] is False
        assert d["unread_count"] == 0
        assert "date_joined" in d
        # Verify password is hashed, not stored in plaintext
        user = User.objects.get(username="newuser")
        assert user.check_password("ValidPass1!")

    def test_duplicate_username_returns_error(self, client, alice):
        resp = client.post(BASE + "register/", {
            "username": "alice",
            "password": "ValidPass1!",
            "nickname": "Fake Alice",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["data"] is None

    def test_weak_password_missing_letter_returns_error(self, client):
        resp = client.post(BASE + "register/", {
            "username": "user1",
            "password": "12345678!",
            "nickname": "User1",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["data"] is None

    def test_weak_password_missing_digit_returns_error(self, client):
        resp = client.post(BASE + "register/", {
            "username": "user2",
            "password": "abcdefgh!",
            "nickname": "User2",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["data"] is None

    def test_weak_password_missing_special_returns_error(self, client):
        resp = client.post(BASE + "register/", {
            "username": "user3",
            "password": "abcd1234",
            "nickname": "User3",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["data"] is None

    def test_weak_password_too_short_returns_error(self, client):
        resp = client.post(BASE + "register/", {
            "username": "user4",
            "password": "Ab1!",
            "nickname": "User4",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["data"] is None

    def test_register_without_nickname_uses_username_as_nickname(self, client):
        """nickname is required via serializer; if omitted, serializer catches it."""
        resp = client.post(BASE + "register/", {
            "username": "nonick",
            "password": "ValidPass1!",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["data"] is None

    def test_register_without_email_uses_none(self, client):
        """email is optional (allow_blank=True, required=False, null=True)."""
        resp = client.post(BASE + "register/", {
            "username": "noemail",
            "password": "ValidPass1!",
            "nickname": "No Email",
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["data"]["email"] is None


# ── LoginView ─────────────────────────────────────────────────
# 匿名限流由根 conftest 的 _no_anon_throttle 全局关闭

@pytest.mark.django_db
class TestLoginView:
    def test_success_with_correct_credentials(self, client, alice):
        resp = client.post(BASE + "login/", {
            "username": "alice",
            "password": "Pass1234!",
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["code"] == 0
        d = resp.data["data"]
        assert d["user_id"] == alice.id
        assert d["username"] == "alice"

    def test_wrong_password_returns_401(self, client, alice):
        resp = client.post(BASE + "login/", {
            "username": "alice",
            "password": "WrongPass1!",
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert resp.data["code"] == 40003
        assert resp.data["message"] == "用户名或密码错误"
        assert resp.data["data"] is None

    def test_non_existent_user_returns_401(self, client):
        resp = client.post(BASE + "login/", {
            "username": "nobody",
            "password": "Pass1234!",
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert resp.data["code"] == 40003
        assert resp.data["message"] == "用户名或密码错误"
        assert resp.data["data"] is None

    def test_missing_fields_returns_401(self, client):
        resp = client.post(BASE + "login/", {})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert resp.data["code"] == 40003

    def test_partial_fields_returns_401(self, client):
        resp = client.post(BASE + "login/", {"username": "alice"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert resp.data["code"] == 40003

    def test_login_uses_session_auth(self, client, alice):
        """Real SessionAuthentication: login creates session, subsequent
        requests from same client are authenticated."""
        resp = client.post(BASE + "login/", {
            "username": "alice",
            "password": "Pass1234!",
        })
        assert resp.status_code == status.HTTP_200_OK
        resp2 = client.get(BASE + "me/")
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.data["data"]["user_id"] == alice.id


# ── LogoutView ────────────────────────────────────────────────

@pytest.mark.django_db
class TestLogoutView:
    def test_success_when_authenticated(self, alice_client):
        resp = alice_client.post(BASE + "logout/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["code"] == 0

    def test_returns_403_when_not_authenticated(self, client):
        resp = client.post(BASE + "logout/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["data"] is None


# ── MeView ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMeView:
    def test_get_returns_full_profile(self, alice_client, alice):
        resp = alice_client.get(BASE + "me/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["code"] == 0
        d = resp.data["data"]
        assert d["user_id"] == alice.id
        assert d["username"] == "alice"
        assert d["nickname"] == "Alice"
        assert "real_name" in d
        assert "avatar_url" in d
        assert "cover_url" in d
        assert "bio" in d
        assert "email" in d
        assert "show_real_name" in d
        assert "visitor_public" in d
        assert "is_admin" in d
        assert "date_joined" in d
        assert "unread_count" in d

    def test_get_returns_403_when_not_authenticated(self, client):
        resp = client.get(BASE + "me/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["data"] is None

    def test_patch_nickname_bio_email(self, alice_client, alice):
        resp = alice_client.patch(BASE + "me/", {
            "nickname": "Alice Updated",
            "bio": "New bio",
            "email": "alice_new@example.com",
        })
        assert resp.status_code == status.HTTP_200_OK
        alice.refresh_from_db()
        assert alice.nickname == "Alice Updated"
        assert alice.bio == "New bio"
        assert alice.email == "alice_new@example.com"
        d = resp.data["data"]
        assert d["nickname"] == "Alice Updated"
        assert d["bio"] == "New bio"
        assert d["email"] == "alice_new@example.com"

    def test_patch_show_real_name_true(self, alice_client, alice):
        alice.real_name = "Alice Real"
        alice.save()
        resp = alice_client.patch(BASE + "me/", {"show_real_name": True})
        assert resp.status_code == status.HTTP_200_OK
        profile = UserProfile.objects.get(user=alice)
        assert profile.show_real_name is True

    def test_patch_visitor_public_false(self, alice_client, alice):
        resp = alice_client.patch(BASE + "me/", {"visitor_public": False})
        assert resp.status_code == status.HTTP_200_OK
        profile = UserProfile.objects.get(user=alice)
        assert profile.visitor_public is False

    def test_patch_show_real_name_false_then_true(self, alice_client, alice):
        alice.real_name = "Alice Real"
        alice.save()
        resp = alice_client.patch(BASE + "me/", {"show_real_name": False})
        assert resp.status_code == status.HTTP_200_OK
        assert UserProfile.objects.get(user=alice).show_real_name is False
        resp = alice_client.patch(BASE + "me/", {"show_real_name": True})
        assert resp.status_code == status.HTTP_200_OK
        assert UserProfile.objects.get(user=alice).show_real_name is True

    def test_patch_partial_does_not_affect_other_fields(self, alice_client, alice):
        alice.nickname = "Original"
        alice.bio = "Original bio"
        alice.save()
        resp = alice_client.patch(BASE + "me/", {"nickname": "Only Nick"})
        assert resp.status_code == status.HTTP_200_OK
        alice.refresh_from_db()
        assert alice.nickname == "Only Nick"
        assert alice.bio == "Original bio"

    def test_patch_returns_403_when_not_authenticated(self, client):
        resp = client.patch(BASE + "me/", {"nickname": "Hacker"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["data"] is None


# ── ChangePasswordView ────────────────────────────────────────

@pytest.mark.django_db
class TestChangePasswordView:
    def test_success_with_correct_old_password(self, alice_client, alice):
        resp = alice_client.post(BASE + "change-password/", {
            "old_password": "Pass1234!",
            "new_password": "NewPass123!",
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["code"] == 0
        alice.refresh_from_db()
        assert alice.check_password("NewPass123!")

    def test_wrong_old_password_returns_error(self, alice_client):
        resp = alice_client.post(BASE + "change-password/", {
            "old_password": "WrongPass1!",
            "new_password": "NewPass123!",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40003
        assert resp.data["message"] == "旧密码不正确"
        assert resp.data["data"] is None

    def test_new_password_too_short_returns_error(self, alice_client):
        resp = alice_client.post(BASE + "change-password/", {
            "old_password": "Pass1234!",
            "new_password": "Ab1!",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert resp.data["message"] == "新密码长度不能少于8位"
        assert resp.data["data"] is None

    def test_new_password_missing_letter_returns_error(self, alice_client):
        resp = alice_client.post(BASE + "change-password/", {
            "old_password": "Pass1234!",
            "new_password": "12345678!",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert resp.data["message"] == "新密码必须包含字母"

    def test_new_password_missing_digit_returns_error(self, alice_client):
        resp = alice_client.post(BASE + "change-password/", {
            "old_password": "Pass1234!",
            "new_password": "abcdefgh!",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert resp.data["message"] == "新密码必须包含数字"

    def test_new_password_missing_special_returns_error(self, alice_client):
        resp = alice_client.post(BASE + "change-password/", {
            "old_password": "Pass1234!",
            "new_password": "abcd1234",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert resp.data["message"] == "新密码必须包含至少一个特殊字符"

    def test_missing_old_password_returns_error(self, alice_client):
        resp = alice_client.post(BASE + "change-password/", {
            "new_password": "NewPass123!",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert resp.data["message"] == "请提供旧密码和新密码"

    def test_missing_new_password_returns_error(self, alice_client):
        resp = alice_client.post(BASE + "change-password/", {
            "old_password": "Pass1234!",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert resp.data["message"] == "请提供旧密码和新密码"

    def test_returns_403_when_not_authenticated(self, client):
        resp = client.post(BASE + "change-password/", {
            "old_password": "x",
            "new_password": "y",
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["data"] is None


# ── AvatarUploadView ──────────────────────────────────────────

@pytest.mark.django_db
class TestAvatarUploadView:
    def test_success_returns_avatar_url(self, alice_client, alice, fake_image):
        resp = alice_client.post(BASE + "avatar/", {"avatar": fake_image}, format="multipart")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["code"] == 0
        assert resp.data["data"]["avatar_url"] is not None
        alice.refresh_from_db()
        assert alice.avatar is not None

    def test_invalid_file_type_returns_error(self, alice_client):
        bad = _non_image_file()
        resp = alice_client.post(BASE + "avatar/", {"avatar": bad}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert resp.data["data"] is None

    def test_missing_file_returns_error(self, alice_client):
        resp = alice_client.post(BASE + "avatar/", {}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert resp.data["message"] == "请上传头像文件"

    def test_returns_403_when_not_authenticated(self, client, fake_image):
        resp = client.post(BASE + "avatar/", {"avatar": fake_image}, format="multipart")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["data"] is None

    def test_rejects_non_image_content(self, alice_client):
        """A .jpg file that is not really an image should be rejected."""
        fake_jpg = SimpleUploadedFile("fake.jpg", b"not a real image", content_type="image/jpeg")
        resp = alice_client.post(BASE + "avatar/", {"avatar": fake_jpg}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001

    def test_avatar_persisted_across_requests(self, alice_client, alice, fake_image):
        alice_client.post(BASE + "avatar/", {"avatar": fake_image}, format="multipart")
        alice.refresh_from_db()
        assert alice.avatar.name.startswith("avatars/")


# ── CoverUploadView ───────────────────────────────────────────

@pytest.mark.django_db
class TestCoverUploadView:
    def test_success_returns_cover_url(self, alice_client, alice, fake_image):
        resp = alice_client.post(BASE + "cover/", {"cover_image": fake_image}, format="multipart")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["code"] == 0
        assert resp.data["data"]["cover_url"] is not None
        alice.refresh_from_db()
        assert alice.cover_image is not None

    def test_invalid_file_type_returns_error(self, alice_client):
        bad = _non_image_file()
        resp = alice_client.post(BASE + "cover/", {"cover_image": bad}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert resp.data["data"] is None

    def test_missing_file_returns_error(self, alice_client):
        resp = alice_client.post(BASE + "cover/", {}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001
        assert resp.data["message"] == "请上传封面文件"

    def test_returns_403_when_not_authenticated(self, client, fake_image):
        resp = client.post(BASE + "cover/", {"cover_image": fake_image}, format="multipart")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["data"] is None

    def test_rejects_non_image_content(self, alice_client):
        fake_jpg = SimpleUploadedFile("fake.jpg", b"not a real image", content_type="image/jpeg")
        resp = alice_client.post(BASE + "cover/", {"cover_image": fake_jpg}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["code"] == 40001

    def test_cover_persisted_across_requests(self, alice_client, alice, fake_image):
        alice_client.post(BASE + "cover/", {"cover_image": fake_image}, format="multipart")
        alice.refresh_from_db()
        assert alice.cover_image.name.startswith("covers/")


# ── ⛓️ 前后端契约验证 ─────────────────────────────────────────

ALL_USER_FIELDS = {
    "user_id", "username", "nickname", "real_name",
    "avatar_url", "cover_url", "bio", "email",
    "show_real_name", "visitor_public", "is_admin",
    "date_joined", "unread_count",
}

REGISTER_REQUIRED_READONLY = {
    "user_id", "username", "nickname", "real_name",
    "avatar_url", "cover_url", "bio", "email",
    "show_real_name", "visitor_public", "is_admin",
    "date_joined", "unread_count",
}


@pytest.mark.django_db
class TestUserSerializerContract:
    """前端依赖 UserSerializer 的 13 个字段。注册/登录/me 必须返回同一套字段。"""

    def test_register_returns_all_user_fields(self, client):
        resp = client.post(BASE + "register/", {
            "username": "contract_test",
            "password": "ValidPass1!",
            "nickname": "Contract",
        })
        assert resp.status_code == 201
        fields = set(resp.data["data"].keys())
        missing = ALL_USER_FIELDS - fields
        assert not missing, f"注册响应缺少字段: {missing}"

    def test_login_returns_same_fields_as_register(self, client, alice):
        login_resp = client.post(BASE + "login/", {
            "username": "alice",
            "password": "Pass1234!",
        })
        assert login_resp.status_code == 200
        login_fields = set(login_resp.data["data"].keys())
        missing = ALL_USER_FIELDS - login_fields
        assert not missing, f"登录响应缺少字段: {missing}"

    def test_me_returns_same_fields(self, alice_client):
        resp = alice_client.get(BASE + "me/")
        assert resp.status_code == 200
        me_fields = set(resp.data["data"].keys())
        missing = ALL_USER_FIELDS - me_fields
        assert not missing, f"/me 响应缺少字段: {missing}"

    def test_me_patch_preserves_all_fields(self, alice_client):
        alice_client.patch(BASE + "me/", {"bio": "Updated bio"})
        resp = alice_client.get(BASE + "me/")
        fields = set(resp.data["data"].keys())
        missing = ALL_USER_FIELDS - fields
        assert not missing, f"PATCH 后 /me 缺少字段: {missing}"

    def test_field_types_are_consistent(self, client, alice):
        login_resp = client.post(BASE + "login/", {
            "username": "alice",
            "password": "Pass1234!",
        })
        d = login_resp.data["data"]
        assert isinstance(d["user_id"], int)
        assert isinstance(d["username"], str)
        assert isinstance(d["nickname"], str)
        assert isinstance(d["show_real_name"], bool)
        assert isinstance(d["visitor_public"], bool)
        assert isinstance(d["is_admin"], bool)
        assert isinstance(d["unread_count"], int)
        assert d["avatar_url"] is None or isinstance(d["avatar_url"], str)
        assert d["cover_url"] is None or isinstance(d["cover_url"], str)

    def test_register_then_login_ids_match(self, client):
        """注册后登录应返回同一 user_id"""
        reg_resp = client.post(BASE + "register/", {
            "username": "idmatch",
            "password": "ValidPass1!",
            "nickname": "IDMatch",
        })
        reg_id = reg_resp.data["data"]["user_id"]
        client.post(BASE + "logout/")
        login_resp = client.post(BASE + "login/", {
            "username": "idmatch",
            "password": "ValidPass1!",
        })
        login_id = login_resp.data["data"]["user_id"]
        assert login_id == reg_id

    def test_register_with_email_shows_in_response(self, client):
        resp = client.post(BASE + "register/", {
            "username": "emailtest",
            "password": "ValidPass1!",
            "nickname": "Email",
            "email": "test@example.com",
        })
        assert resp.data["data"]["email"] == "test@example.com"

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestC6AdminLogsUserId:
    def test_invalid_user_id_does_not_crash(self):
        client = APIClient()
        admin = User.objects.create_user(
            username="admin", password="pass", is_staff=True
        )
        client.force_authenticate(user=admin)
        response = client.get("/api/v1/admin/logs/", {"user_id": "RL"})
        assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_valid_numeric_user_id_works(self):
        client = APIClient()
        admin = User.objects.create_user(
            username="admin", password="pass", is_staff=True
        )
        user = User.objects.create_user(username="testuser", password="pass")
        client.force_authenticate(user=admin)
        response = client.get("/api/v1/admin/logs/", {"user_id": str(user.id)})
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_403_FORBIDDEN)

    def test_no_user_id_param_works(self):
        client = APIClient()
        admin = User.objects.create_user(
            username="admin", password="pass", is_staff=True
        )
        client.force_authenticate(user=admin)
        response = client.get("/api/v1/admin/logs/")
        assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR

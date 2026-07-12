import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.groups.models import InterestGroup, GroupMember

User = get_user_model()


@pytest.mark.django_db
class TestC8GroupTransfer:
    def test_invalid_new_owner_id_does_not_crash(self):
        client = APIClient()
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        group = InterestGroup.objects.create(name="Test", creator=alice, is_public=True)
        GroupMember.objects.create(group=group, user=alice, role="admin")
        GroupMember.objects.create(group=group, user=bob, role="member")
        client.force_authenticate(user=alice)
        response = client.post(f"/api/v1/groups/{group.id}/transfer/", {"new_owner_id": "abc"})
        assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_valid_new_owner_id_succeeds(self):
        client = APIClient()
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        group = InterestGroup.objects.create(name="Test", creator=alice, is_public=True)
        GroupMember.objects.create(group=group, user=alice, role="admin")
        GroupMember.objects.create(group=group, user=bob, role="member")
        client.force_authenticate(user=alice)
        response = client.post(f"/api/v1/groups/{group.id}/transfer/", {"new_owner_id": bob.id})
        assert response.status_code == status.HTTP_200_OK

    def test_missing_new_owner_id_returns_400(self):
        client = APIClient()
        alice = User.objects.create_user(username="alice", password="pass")
        group = InterestGroup.objects.create(name="Test", creator=alice, is_public=True)
        GroupMember.objects.create(group=group, user=alice, role="admin")
        client.force_authenticate(user=alice)
        response = client.post(f"/api/v1/groups/{group.id}/transfer/", {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

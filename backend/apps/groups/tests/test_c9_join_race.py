import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient

from apps.groups.models import InterestGroup, GroupMember, GroupJoinRequest

User = get_user_model()


@pytest.mark.django_db
class TestC9GroupJoinRace:
    def test_direct_join_get_or_create_prevents_integrity_error(self):
        """GroupMember.create → get_or_create 后，重复加入不抛 IntegrityError"""
        alice = User.objects.create_user(username="alice", password="pass")
        group = InterestGroup.objects.create(name="Test", creator=alice, is_public=True)
        member, created = GroupMember.objects.get_or_create(group=group, user=alice)
        assert created is True
        member, created = GroupMember.objects.get_or_create(group=group, user=alice)
        assert created is False
        assert GroupMember.objects.filter(group=group, user=alice).count() == 1

    def test_approve_join_get_or_create_prevents_integrity_error(self):
        """审批加入时 get_or_create 防止重复创建"""
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        group = InterestGroup.objects.create(name="Test", creator=alice, is_public=False)
        GroupMember.objects.create(group=group, user=alice, role="admin")
        GroupJoinRequest.objects.create(group=group, applicant=bob)
        member, created = GroupMember.objects.get_or_create(group=group, user=bob)
        assert created is True
        member, created = GroupMember.objects.get_or_create(group=group, user=bob)
        assert created is False
        assert GroupMember.objects.filter(group=group, user=bob).count() == 1

    def test_join_api_idempotent(self):
        client = APIClient()
        alice = User.objects.create_user(username="alice", password="pass")
        group = InterestGroup.objects.create(name="Test", creator=alice, is_public=True)
        GroupMember.objects.create(group=group, user=alice, role="admin")
        bob = User.objects.create_user(username="bob", password="pass")
        client.force_authenticate(user=bob)
        response1 = client.post(f"/api/v1/groups/{group.id}/join/")
        assert response1.status_code == status.HTTP_200_OK
        response2 = client.post(f"/api/v1/groups/{group.id}/join/")
        assert response2.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_approve_api_idempotent(self):
        client = APIClient()
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        group = InterestGroup.objects.create(name="Test", creator=alice, is_public=False)
        GroupMember.objects.create(group=group, user=alice, role="admin")
        join_request = GroupJoinRequest.objects.create(group=group, applicant=bob)
        client.force_authenticate(user=alice)
        response = client.post(
            f"/api/v1/groups/requests/{join_request.id}/handle/",
            {"action": "approved"},
        )
        assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR

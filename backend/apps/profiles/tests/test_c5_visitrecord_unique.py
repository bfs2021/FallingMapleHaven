import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from apps.profiles.models import VisitRecord

User = get_user_model()


@pytest.mark.django_db
class TestC5VisitRecordUnique:
    def test_duplicate_visitor_visited_raises_integrity_error(self):
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        VisitRecord.objects.create(visitor=alice, visited_user=bob)
        with pytest.raises(IntegrityError):
            VisitRecord.objects.create(visitor=alice, visited_user=bob)

    def test_update_or_create_works_repeatedly(self):
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        VisitRecord.objects.update_or_create(
            visitor=alice,
            visited_user=bob,
            defaults={"visited_at": timezone.now()},
        )
        VisitRecord.objects.update_or_create(
            visitor=alice,
            visited_user=bob,
            defaults={"visited_at": timezone.now()},
        )
        assert VisitRecord.objects.count() == 1

    def test_different_visitors_same_target_allowed(self):
        alice = User.objects.create_user(username="alice", password="pass")
        bob = User.objects.create_user(username="bob", password="pass")
        charlie = User.objects.create_user(username="charlie", password="pass")
        VisitRecord.objects.create(visitor=alice, visited_user=bob)
        VisitRecord.objects.create(visitor=charlie, visited_user=bob)
        assert VisitRecord.objects.count() == 2

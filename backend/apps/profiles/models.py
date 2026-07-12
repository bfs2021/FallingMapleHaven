from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    show_real_name = models.BooleanField(default=False)
    visitor_public = models.BooleanField(default=True)
    layout_config = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profiles_profile"

    def __str__(self):
        return f"{self.user.username}'s profile"


class VisitRecord(models.Model):
    visitor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visit_records",
    )
    visited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visitor_records",
    )
    visited_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "profiles_visitrecord"
        ordering = ["-visited_at"]
        constraints = [
            UniqueConstraint(fields=["visitor", "visited_user"], name="uq_visitor_visited"),
        ]

    def __str__(self):
        return f"{self.visitor.username} visited {self.visited_user.username}"


class GuestbookEntry(models.Model):
    profile = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="guestbook_entries"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    content = models.TextField()
    reply = models.TextField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "profiles_guestbookentry"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Guestbook entry by {self.author.username}"

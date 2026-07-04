from django.conf import settings
from django.db import models


class InterestGroup(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    cover_image = models.FileField(upload_to="groups/covers/", blank=True, null=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_groups",
    )
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "groups_interestgroup"

    def __str__(self):
        return self.name


class GroupMember(models.Model):
    group = models.ForeignKey(
        InterestGroup, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_memberships"
    )
    role = models.CharField(
        max_length=20, choices=[("admin", "管理员"), ("member", "成员")], default="member"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "groups_groupmember"
        constraints = [
            models.UniqueConstraint(
                fields=["group", "user"], name="uq_group_member"
            )
        ]

    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.role})"


class GroupJoinRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待处理"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已拒绝"

    group = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, related_name="join_requests")
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_join_requests")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="handled_join_requests")
    handled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "groups_groupjoinrequest"
        constraints = [
            models.UniqueConstraint(fields=["group", "applicant"], name="uq_group_join_request")
        ]

    def __str__(self):
        return f"{self.applicant.username} -> {self.group.name} ({self.status})"

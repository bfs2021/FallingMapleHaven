from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        SYSTEM = "system", "系统通知"
        FRIEND_REQUEST = "friend_request", "好友请求"
        FRIEND_ACCEPTED = "friend_accepted", "好友请求接受"
        COMMENT = "comment", "评论"
        LIKE = "like", "点赞"
        REPLY = "reply", "回复"
        QUIZ_INVITE = "quiz_invite", "默契问答邀请"
        ANONYMOUS_QUESTION = "anonymous_question", "匿名提问"
        GROUP_JOIN_REQUEST = "group_join_request", "加入小组申请"
        GROUP_REQUEST_APPROVED = "group_request_approved", "加入申请通过"
        GROUP_REQUEST_REJECTED = "group_request_rejected", "加入申请拒绝"
        GROUP_MEMBER_JOINED = "group_member_joined", "新成员加入"
        GROUP_NEW_POST = "group_new_post", "小组新动态"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
    )
    type = models.CharField(max_length=50, choices=Type.choices)
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True, null=True)
    link = models.CharField(max_length=500, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type} to {self.recipient.username}"

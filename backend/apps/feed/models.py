from django.conf import settings
from django.db import models


class Post(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "公开"
        FRIENDS = "friends", "好友可见"
        PRIVATE = "private", "仅自己"

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    group = models.ForeignKey(
        "groups.InterestGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
    )
    content = models.TextField()
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    topic_tag = models.CharField(max_length=50, blank=True, default="")
    sync_to_profile = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "feed_post"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Post by {self.author.username}"


class PostImage(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="images"
    )
    image = models.FileField(upload_to="feed/images/")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "feed_postimage"
        ordering = ["order"]

    def __str__(self):
        return f"Image for post {self.post_id}"


class PostFile(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="files"
    )
    file = models.FileField(upload_to="feed/files/")
    name = models.CharField(max_length=255)
    size = models.BigIntegerField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "feed_postfile"
        ordering = ["order"]

    def __str__(self):
        return self.name


class Comment(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    content = models.TextField()
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "feed_comment"
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username}"


class Like(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="likes"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "feed_like"
        constraints = [
            models.UniqueConstraint(
                fields=["post", "user"], name="uq_feed_like_post_user"
            )
        ]

    def __str__(self):
        return f"{self.user.username} liked post {self.post_id}"

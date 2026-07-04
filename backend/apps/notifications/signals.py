from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.feed.models import Comment, Like
from apps.friends.models import Friendship
from apps.notifications.models import Notification


@receiver(post_save, sender=Friendship)
def handle_friend_request(sender, instance, created, **kwargs):
    if created and instance.status == Friendship.Status.PENDING:
        Notification.objects.create(
            recipient=instance.to_user,
            sender=instance.from_user,
            notification_type=Notification.Type.FRIEND_REQUEST,
            title="好友请求",
            content=f"{instance.from_user.nickname} 请求添加你为好友",
            link="",
        )
    elif instance.status == Friendship.Status.ACCEPTED:
        Notification.objects.create(
            recipient=instance.from_user,
            sender=instance.to_user,
            notification_type=Notification.Type.FRIEND_ACCEPTED,
            title="好友请求已接受",
            content=f"{instance.to_user.nickname} 已接受你的好友请求",
            link="",
        )


@receiver(post_save, sender=Like)
def handle_like(sender, instance, created, **kwargs):
    if created and instance.post.author != instance.user:
        Notification.objects.create(
            recipient=instance.post.author,
            sender=instance.user,
            notification_type=Notification.Type.LIKE,
            title="收到点赞",
            content=f"{instance.user.nickname} 赞了你的动态",
            link="/",
        )


@receiver(post_save, sender=Comment)
def handle_comment(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.post.author != instance.author:
        Notification.objects.create(
            recipient=instance.post.author,
            sender=instance.author,
            notification_type=Notification.Type.COMMENT,
            title="收到评论",
            content=f"{instance.author.nickname} 评论了你的动态: {instance.content[:50]}",
            link="/",
        )

    if instance.parent and instance.parent.author != instance.author:
        Notification.objects.create(
            recipient=instance.parent.author,
            sender=instance.author,
            notification_type=Notification.Type.REPLY,
            title="收到回复",
            content=f"{instance.author.nickname} 回复了你的评论: {instance.content[:50]}",
            link="/",
        )

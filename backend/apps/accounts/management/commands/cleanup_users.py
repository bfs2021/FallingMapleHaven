import os
import shutil
from collections import defaultdict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Q

User = get_user_model()

EXCLUDED_USERNAMES = {"RL_RedLeaf", "TestRL1"}

# Map display name -> (app_label, model_name, filter_field)
RELATED_MODELS = [
    ("UserProfile", "profiles.UserProfile", "user__in"),
    ("Friendship (sent)", "friends.Friendship", "from_user__in"),
    ("Friendship (received)", "friends.Friendship", "to_user__in"),
    ("Post", "feed.Post", "author__in"),
    ("Comment", "feed.Comment", "author__in"),
    ("Like", "feed.Like", "user__in"),
    ("ChatRoomMember", "chat.ChatRoomMember", "user__in"),
    ("Message", "chat.Message", "sender__in"),
    ("MessageRead", "chat.MessageRead", "user__in"),
    ("InterestGroup", "groups.InterestGroup", "creator__in"),
    ("GroupMember", "groups.GroupMember", "user__in"),
    ("Notification (recipient)", "notifications.Notification", "recipient__in"),
    ("VisitRecord (as visitor)", "profiles.VisitRecord", "visitor__in"),
    ("VisitRecord (as visited)", "profiles.VisitRecord", "visited_user__in"),
    ("GuestbookEntry", "profiles.GuestbookEntry", "author__in"),
    ("QuizTest", "plugins.QuizTest", "owner__in"),
    ("QuizSubmission", "plugins.QuizSubmission", "user__in"),
    ("AnonymousQuestion (sent)", "plugins.AnonymousQuestion", "sender__in"),
    ("AnonymousQuestion (received)", "plugins.AnonymousQuestion", "recipient__in"),
]


class Command(BaseCommand):
    help = "删除除 RL_RedLeaf 和 TestRL1 之外的所有用户及其关联数据，并清理孤立媒体文件"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="仅预览要删除的内容，不实际执行删除",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="跳过确认提示",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]
        user_ids = list(
            User.objects.exclude(Q(username__in=EXCLUDED_USERNAMES)).values_list(
                "id", flat=True
            )
        )

        total = len(user_ids)
        if total == 0:
            self.stdout.write(self.style.SUCCESS("没有需要删除的用户"))
            return

        users = User.objects.filter(id__in=user_ids)
        self.stdout.write(f"找到 {total} 个要删除的用户:")
        for u in users:
            self.stdout.write(f"  - {u.username} (id={u.id})")

        if dry_run:
            stats = self._collect_stats(user_ids)
            self._print_stats(stats, user_ids)
            return

        if not force:
            confirm = input(f"\n确认删除上述 {total} 个用户及其所有关联数据？(yes/no): ")
            if confirm.lower() != "yes":
                self.stdout.write(self.style.WARNING("已取消"))
                return

        self._delete_users(user_ids)
        self._cleanup_orphaned_media(user_ids)

        self.stdout.write(self.style.SUCCESS(f"成功删除 {len(user_ids)} 个用户及其关联数据"))

    def _collect_stats(self, user_ids):
        stats = {}
        for label, model_path, filter_field in RELATED_MODELS:
            try:
                app_label, model_name = model_path.split(".")
                model = self._get_model(app_label, model_name)
                count = model._base_manager.filter(
                    **{filter_field: user_ids}
                ).count()
                if count:
                    stats[label] = count
            except LookupError:
                pass
        return stats

    def _print_stats(self, stats, user_ids):
        self.stdout.write("\n将删除的关联数据:")
        for label, count in sorted(stats.items()):
            self.stdout.write(f"  {label}: {count}")

        from django.apps import apps
        try:
            ntf_model = apps.get_model("notifications", "Notification")
            sender_null = ntf_model._base_manager.filter(
                sender_id__in=user_ids
            ).count()
            if sender_null:
                self.stdout.write(
                    f"  Notification.sender (SET_NULL): {sender_null}"
                )
        except LookupError:
            pass
        try:
            slog_model = apps.get_model("admin_dashboard", "SiteLog")
            slog_null = slog_model._base_manager.filter(
                user_id__in=user_ids
            ).count()
            if slog_null:
                self.stdout.write(
                    f"  SiteLog.user (SET_NULL): {slog_null}"
                )
        except LookupError:
            pass

    def _delete_users(self, user_ids):
        User.objects.filter(id__in=user_ids).delete()

    def _cleanup_orphaned_media(self, user_ids):
        users = User.objects.filter(id__in=user_ids)
        for user in users:
            for field_name in ("avatar", "cover_image"):
                field_file = getattr(user, field_name, None)
                if field_file and os.path.isfile(field_file.path):
                    try:
                        os.remove(field_file.path)
                        self.stdout.write(f"  已删除文件: {field_file.path}")
                    except OSError as e:
                        self.stdout.write(
                            self.style.WARNING(f"  无法删除 {field_file.path}: {e}")
                        )

    def _get_model(self, app_label, model_name):
        from django.apps import apps
        return apps.get_model(app_label, model_name)

from django.db import migrations


def backfill_chat_rooms(apps, schema_editor):
    InterestGroup = apps.get_model("groups", "InterestGroup")
    ChatRoom = apps.get_model("chat", "ChatRoom")
    ChatRoomMember = apps.get_model("chat", "ChatRoomMember")

    for group in InterestGroup.objects.filter(chat_rooms__isnull=True).iterator():
        room = ChatRoom.objects.create(
            name=group.name,
            type="group",
            is_group=True,
            group=group,
        )
        creator_member = group.members.filter(role="admin").first()
        if creator_member:
            ChatRoomMember.objects.create(room=room, user=creator_member.user)


class Migration(migrations.Migration):

    dependencies = [
        ("groups", "0002_alter_groupmember_user_groupjoinrequest"),
        ("chat", "0003_chatroom_group_message_file"),
    ]

    operations = [
        migrations.RunPython(backfill_chat_rooms, migrations.RunPython.noop),
    ]

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_chatroom_group_message_file'),
    ]

    operations = [
        migrations.RenameField(
            model_name='chatroom',
            old_name='type',
            new_name='room_type',
        ),
    ]

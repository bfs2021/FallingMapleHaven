from ..base import BasePlugin
from ..registry import register_plugin


@register_plugin
class QuizPlugin(BasePlugin):
    plugin_type = "quiz"
    display_name = "默契问答"
    description = "来测测你有多了解我"
    icon = "help-circle"

    def get_profile_data(self, user_id):
        from .models import QuizTest

        published_count = QuizTest.objects.filter(
            owner_id=user_id,
            status=QuizTest.Status.PUBLISHED,
        ).count()
        return {
            "type": self.plugin_type,
            "name": self.display_name,
            "icon": self.icon,
            "description": self.description,
            "data": {
                "entry_text": self.description,
                "published_test_count": published_count,
            },
            "route": f"/profile/{user_id}/plugins/quiz",
        }

    def get_admin_config(self):
        return {
            "sidebar": [
                {
                    "path": "quizzes",
                    "name": "问答管理",
                    "icon": "puzzle",
                }
            ]
        }

    def get_summary(self, user_id):
        return self.get_profile_data(user_id)

    def get_profile_card_data(self, viewer_id, owner_id):
        return self.get_profile_data(owner_id)

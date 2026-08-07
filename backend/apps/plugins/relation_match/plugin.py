from __future__ import annotations

from ..base import BasePlugin
from ..registry import register_plugin


@register_plugin
class RelationMatchPlugin(BasePlugin):
    plugin_type = "relation_match"
    display_name = "关系匹配"
    description = "看看你们像什么"
    icon = "heart-handshake"

    def get_profile_data(self, user_id):
        from .models import RelationMatchProfile, RelationMatchTest

        has_profile = RelationMatchProfile.objects.filter(user_id=user_id).exists()
        active_test = RelationMatchTest.objects.filter(slug="current").first()
        return {
            "type": self.plugin_type,
            "name": self.display_name,
            "icon": self.icon,
            "description": self.description,
            "data": {
                "has_profile": has_profile,
                "current_test_id": active_test.id if active_test else None,
            },
            "route": f"/profile/{user_id}/plugins/relation-match",
        }

    def get_admin_config(self):
        return {
            "sidebar": [
                {
                    "path": "relation-match",
                    "name": "关系匹配管理",
                    "icon": "puzzle",
                }
            ]
        }

    def get_summary(self, user_id):
        return self.get_profile_data(user_id)

    def get_profile_card_data(self, viewer_id, owner_id):
        return self.get_profile_data(owner_id)

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.plugins.registry import PluginRegistry


class ActivePluginsView(APIView):
    def get(self, request):
        plugins = PluginRegistry.get_active_plugins()
        data = [
            {
                "type": p.plugin_type,
                "name": p.display_name,
                "icon": p.icon,
                "description": p.description,
            }
            for p in plugins.values()
        ]
        return Response({"code": 0, "message": "success", "data": data})


class PluginSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.plugins.registry import PluginRegistry
        from apps.plugins.models import Plugin as PluginModel

        active_types = set(
            PluginModel.objects.filter(is_active=True).values_list("plugin_type", flat=True)
        )
        summaries = []
        for plugin in PluginRegistry.get_all_plugins().values():
            summary = plugin.get_summary(request.user.id)
            summary["is_active"] = plugin.plugin_type in active_types
            summaries.append(summary)
        return Response({"code": 0, "data": summaries})


class ProfilePluginCardsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        from apps.plugins.registry import PluginRegistry
        from apps.plugins.models import Plugin as PluginModel
        from apps.profiles.models import GuestbookEntry

        viewer_id = request.user.id if request.user.is_authenticated else None

        active_types = set(
            PluginModel.objects.filter(is_active=True).values_list("plugin_type", flat=True)
        )
        cards = []
        for plugin in PluginRegistry.get_all_plugins().values():
            if plugin.plugin_type not in active_types:
                continue
            data = plugin.get_profile_card_data(viewer_id, user_id)
            if data:
                cards.append(data)

        total_gb = GuestbookEntry.objects.filter(profile__user_id=user_id).count()
        cards.append({
            "type": "guestbook",
            "name": "留言板",
            "icon": "message-square",
            "description": "给我留言",
            "data": {"total_messages": total_gb},
            "route": f"/profile/{user_id}/guestbook",
        })
        return Response({"code": 0, "data": cards})

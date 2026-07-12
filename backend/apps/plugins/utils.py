from rest_framework import status

from apps.common.utils import api_response
from apps.plugins.models import Plugin


def ensure_plugin_active(plugin_type: str):
    if not Plugin.objects.filter(plugin_type=plugin_type, is_active=True).exists():
        return api_response(
            code=40004,
            message="插件未启用",
            data=None,
            status=status.HTTP_404_NOT_FOUND,
        )
    return None

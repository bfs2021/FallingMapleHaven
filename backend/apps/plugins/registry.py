class PluginRegistry:
    _plugins = {}

    @classmethod
    def register(cls, plugin_class):
        instance = plugin_class()
        cls._plugins[instance.plugin_type] = instance
        return plugin_class

    @classmethod
    def get_plugin(cls, plugin_type):
        return cls._plugins.get(plugin_type)

    @classmethod
    def get_active_plugins(cls):
        from .models import Plugin
        active_types = Plugin.objects.filter(is_active=True).values_list("plugin_type", flat=True)
        return {ptype: cls._plugins[ptype] for ptype in active_types if ptype in cls._plugins}

    @classmethod
    def get_all_plugins(cls):
        return dict(cls._plugins)

    @classmethod
    def get_profile_plugins(cls, user_id: int) -> list:
        result = []
        for plugin in cls.get_active_plugins().values():
            data = plugin.get_profile_data(user_id)
            if data:
                result.append(data)
        return result


def register_plugin(cls):
    PluginRegistry.register(cls)
    return cls

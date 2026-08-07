from django.apps import AppConfig


class PluginsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.plugins"

    def ready(self):
        import apps.plugins.quizzes.plugin  # noqa: F401
        import apps.plugins.questions.plugin  # noqa: F401
        import apps.plugins.relation_match.plugin  # noqa: F401

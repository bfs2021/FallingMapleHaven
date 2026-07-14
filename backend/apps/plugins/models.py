from django.db import models


class Plugin(models.Model):
    name = models.CharField(max_length=100)
    plugin_type = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "plugins_plugin"

    def __str__(self):
        return self.name


import apps.plugins.quizzes.models  # noqa: F401,E402
import apps.plugins.questions.models  # noqa: F401,E402

from django.urls import include, path
from apps.plugins.views import ActivePluginsView, PluginSummaryView, ProfilePluginCardsView

urlpatterns = [
    path("", ActivePluginsView.as_view(), name="plugin-list"),
    path("summary/", PluginSummaryView.as_view(), name="plugin-summary"),
    path("profile-cards/<str:username_or_id>/", ProfilePluginCardsView.as_view(), name="profile-plugin-cards"),
    path("quiz/", include("apps.plugins.quizzes.urls")),
    path("question-box/", include("apps.plugins.questions.urls")),
]

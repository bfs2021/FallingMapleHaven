from django.urls import path

from .views import (
    RelationMatchCurrentTestSubmissionView,
    RelationMatchCurrentTestView,
    RelationMatchHomeView,
    RelationMatchMyView,
    RelationMatchMyPairsView,
    RelationMatchPairDetailView,
    RelationMatchShareDetailView,
    RelationMatchShareMatchView,
)

urlpatterns = [
    path("users/<int:owner_id>/", RelationMatchHomeView.as_view(), name="relation-match-home"),
    path("tests/current/", RelationMatchCurrentTestView.as_view(), name="relation-match-current-test"),
    path(
        "tests/current/submissions/",
        RelationMatchCurrentTestSubmissionView.as_view(),
        name="relation-match-current-submission",
    ),
    path("shares/<str:share_code>/", RelationMatchShareDetailView.as_view(), name="relation-match-share-detail"),
    path("shares/<str:share_code>/match/", RelationMatchShareMatchView.as_view(), name="relation-match-share-match"),
    path("pairs/<int:result_id>/", RelationMatchPairDetailView.as_view(), name="relation-match-pair-detail"),
    path("my/", RelationMatchMyView.as_view(), name="relation-match-my"),
    path("my/pairs/", RelationMatchMyPairsView.as_view(), name="relation-match-my-pairs"),
]

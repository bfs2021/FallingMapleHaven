from django.urls import path

from .views import (
    RelationMatchCurrentTestSubmissionView,
    RelationMatchCurrentTestView,
    RelationMatchHomeView,
    RelationMatchPairDetailView,
    RelationMatchShareMatchView,
    RelationMatchMyPairsView,
)

urlpatterns = [
    path("users/<int:owner_id>/", RelationMatchHomeView.as_view(), name="relation-match-home"),
    path("tests/current/", RelationMatchCurrentTestView.as_view(), name="relation-match-current-test"),
    path(
        "tests/current/submissions/",
        RelationMatchCurrentTestSubmissionView.as_view(),
        name="relation-match-current-submission",
    ),
    path("shares/<str:share_code>/match/", RelationMatchShareMatchView.as_view(), name="relation-match-share-match"),
    path("pairs/<int:result_id>/", RelationMatchPairDetailView.as_view(), name="relation-match-pair-detail"),
    path("my/pairs/", RelationMatchMyPairsView.as_view(), name="relation-match-my-pairs"),
]

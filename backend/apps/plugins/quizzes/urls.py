from django.urls import path

from apps.plugins.quizzes.views import (
    MyQuizSubmissionsView,
    MyQuizTestDetailView,
    MyQuizTestsView,
    PublicQuizTestDetailView,
    PublicQuizTestsView,
    PublishQuizTestView,
    QuizQuestionBankView,
    QuizTestLeaderboardView,
    SubmitQuizTestView,
)

urlpatterns = [
    path("users/<int:owner_id>/tests/", PublicQuizTestsView.as_view(), name="quiz-public-tests"),
    path("my/tests/", MyQuizTestsView.as_view(), name="quiz-my-tests"),
    path("my/tests/<int:test_id>/", MyQuizTestDetailView.as_view(), name="quiz-my-test-detail"),
    path("my/tests/<int:test_id>/publish/", PublishQuizTestView.as_view(), name="quiz-publish-test"),
    path("tests/<int:test_id>/", PublicQuizTestDetailView.as_view(), name="quiz-public-test-detail"),
    path("tests/<int:test_id>/submissions/", SubmitQuizTestView.as_view(), name="quiz-submit-test"),
    path("tests/<int:test_id>/leaderboard/", QuizTestLeaderboardView.as_view(), name="quiz-test-leaderboard"),
    path("my/submissions/", MyQuizSubmissionsView.as_view(), name="quiz-my-submissions"),
    path("question-bank/", QuizQuestionBankView.as_view(), name="quiz-question-bank"),
]

from django.urls import path
from apps.plugins.quizzes.views import (
    QuizQuestionCreateView,
    QuizReceivedQuestionsView,
    QuizAnswerView,
    QuizQuestionDeleteView,
    QuizResultView,
    QuizLeaderboardView,
)

urlpatterns = [
    path("questions/", QuizQuestionCreateView.as_view(), name="quiz-create"),
    path("questions/received/", QuizReceivedQuestionsView.as_view(), name="quiz-received"),
    path("questions/<int:pk>/answer/", QuizAnswerView.as_view(), name="quiz-answer"),
    path("questions/<int:pk>/delete/", QuizQuestionDeleteView.as_view(), name="quiz-delete"),
    path("result/<int:friend_id>/", QuizResultView.as_view(), name="quiz-result"),
    path("leaderboard/", QuizLeaderboardView.as_view(), name="quiz-leaderboard"),
]

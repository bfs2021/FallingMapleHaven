from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.plugins.utils import ensure_plugin_active
from .models import QuizQuestion, QuizAnswer, QuizResult
from .serializers import (
    QuizQuestionCreateSerializer,
    QuizQuestionSerializer,
    QuizAnswerSerializer,
    QuizResultSerializer,
)


class QuizQuestionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        inactive = ensure_plugin_active("quiz")
        if inactive:
            return inactive

        serializer = QuizQuestionCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        question = QuizQuestion.objects.create(
            creator=request.user,
            target_user_id=serializer.validated_data["target_user_id"],
            question=serializer.validated_data["question"],
            correct_answer=serializer.validated_data["correct_answer"],
        )
        Notification.objects.create(
            recipient_id=serializer.validated_data["target_user_id"],
            sender=request.user,
            type=Notification.Type.QUIZ_INVITE,
            title="默契问答邀请",
            content=f"{request.user.nickname} 向你出了一道题",
            link=f"/profile/{question.target_user_id}/plugins/quiz",
        )
        return Response(
            {"code": 0, "message": "success", "data": QuizQuestionSerializer(question).data},
            status=status.HTTP_201_CREATED,
        )


class QuizReceivedQuestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        inactive = ensure_plugin_active("quiz")
        if inactive:
            return inactive

        answered = request.query_params.get("answered", "false").lower() == "true"
        questions = QuizQuestion.objects.filter(target_user=request.user)
        if not answered:
            questions = questions.filter(answer__isnull=True)
        else:
            questions = questions.filter(answer__isnull=False)
        questions = questions.order_by("-created_at")
        serializer = QuizQuestionSerializer(questions, many=True)
        return Response({"code": 0, "message": "success", "data": serializer.data})


class QuizAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        inactive = ensure_plugin_active("quiz")
        if inactive:
            return inactive

        with transaction.atomic():
            try:
                question = QuizQuestion.objects.select_for_update().get(pk=pk, target_user=request.user)
            except QuizQuestion.DoesNotExist:
                return Response(
                    {"code": 1, "message": "题目不存在或无权限"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if QuizAnswer.objects.filter(question=question).exists():
                return Response(
                    {"code": 1, "message": "该题目已作答"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            answer = request.data.get("answer", "")
            is_correct = answer.strip() == question.correct_answer.strip()

            try:
                QuizAnswer.objects.create(
                    question=question,
                    answerer=request.user,
                    answer=answer,
                    is_correct=is_correct,
                )
            except IntegrityError:
                return Response(
                    {"code": 1, "message": "该题目已作答"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        self._update_result(request.user, question.creator)

        creator_result = QuizResult.objects.filter(
            Q(user_a=question.creator, user_b=request.user)
            | Q(user_a=request.user, user_b=question.creator)
        ).first()

        return Response(
            {
                "code": 0,
                "message": "success",
                "data": {
                    "is_correct": is_correct,
                    "correct_answer": question.correct_answer,
                    "match_score": float(creator_result.match_score) if creator_result else 0,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    def _update_result(self, answerer, creator):
        questions = QuizQuestion.objects.filter(
            Q(creator=creator, target_user=answerer) | Q(creator=answerer, target_user=creator)
        )
        total = questions.count()
        answered_ids = QuizAnswer.objects.filter(
            question__in=questions, answerer__in=[creator, answerer]
        ).values_list("question_id", flat=True)
        correct = QuizAnswer.objects.filter(
            question__in=questions, answerer__in=[creator, answerer], is_correct=True
        ).count()

        if total == 0:
            return

        match_score = round((correct / total) * 100, 2)
        user_a, user_b = (creator, answerer) if creator.id < answerer.id else (answerer, creator)

        QuizResult.objects.update_or_create(
            user_a=user_a,
            user_b=user_b,
            defaults={
                "total_questions": total,
                "correct_count": correct,
                "match_score": match_score,
            },
        )


class QuizQuestionDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        inactive = ensure_plugin_active("quiz")
        if inactive:
            return inactive

        try:
            question = QuizQuestion.objects.get(pk=pk, creator=request.user)
        except QuizQuestion.DoesNotExist:
            return Response(
                {"code": 40004, "message": "题目不存在或无权限"},
                status=status.HTTP_404_NOT_FOUND,
            )
        question.delete()
        return Response({"code": 0, "message": "success", "data": None})


class QuizResultView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, friend_id):
        inactive = ensure_plugin_active("quiz")
        if inactive:
            return inactive

        result = QuizResult.objects.filter(
            Q(user_a=request.user, user_b_id=friend_id)
            | Q(user_a_id=friend_id, user_b=request.user)
        ).first()
        if not result:
            return Response(
                {"code": 40004, "message": "结果不存在", "data": None},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = QuizResultSerializer(result, context={"user_id": request.user.id})
        return Response({"code": 0, "message": "success", "data": serializer.data})


class QuizLeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        inactive = ensure_plugin_active("quiz")
        if inactive:
            return inactive

        from apps.friends.models import Friendship
        from django.db.models import Q

        friends = Friendship.objects.filter(
            Q(sender=request.user, status="accepted") |
            Q(receiver=request.user, status="accepted")
        )
        friend_ids = set()
        for f in friends:
            friend_ids.add(f.sender_id if f.receiver == request.user else f.receiver_id)

        results = QuizResult.objects.filter(
            (Q(user_a=request.user) & Q(user_b_id__in=friend_ids)) |
            (Q(user_b=request.user) & Q(user_a_id__in=friend_ids))
        ).order_by("-match_score", "-total_questions")

        rankings = []
        for i, r in enumerate(results, 1):
            friend = r.user_a if r.user_b == request.user else r.user_b
            rankings.append({
                "rank": i,
                "friend_id": friend.id,
                "nickname": friend.nickname,
                "avatar_url": friend.avatar.url if friend.avatar else None,
                "match_score": float(r.match_score),
                "total_questions": r.total_questions,
                "correct_count": r.correct_count,
            })

        avg = round(
            sum(r["match_score"] for r in rankings) / len(rankings), 1
        ) if rankings else 0

        return Response({"code": 0, "data": {
            "rankings": rankings,
            "avg_match_rate": avg,
            "total_friends": len(rankings),
        }})

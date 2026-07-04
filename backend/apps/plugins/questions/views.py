from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from django.utils.html import strip_tags
from apps.common.utils import safe_int
from apps.plugins.utils import ensure_plugin_active
from .models import AnonymousQuestion
from .serializers import (
    QuestionCreateSerializer,
    QuestionSerializer,
    AdminQuestionSerializer,
    AnswerSerializer,
)


class QuestionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        inactive = ensure_plugin_active("question_box")
        if inactive:
            return inactive

        serializer = QuestionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = AnonymousQuestion.objects.create(
            recipient_id=serializer.validated_data["recipient_id"],
            sender=request.user,
            content=strip_tags(serializer.validated_data["content"]),
            is_public=serializer.validated_data.get("is_public", True),
        )
        Notification.objects.create(
            recipient_id=serializer.validated_data["recipient_id"],
            sender=request.user,
            notification_type=Notification.Type.ANONYMOUS_QUESTION,
            title="收到匿名提问",
            content=strip_tags(serializer.validated_data["content"])[:100],
            link=f"/profile/{serializer.validated_data['recipient_id']}/plugins/question-box",
        )
        return Response(
            {"code": 0, "message": "success", "data": {"id": question.id}},
            status=status.HTTP_201_CREATED,
        )


class InboxView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        inactive = ensure_plugin_active("question_box")
        if inactive:
            return inactive

        answered = request.query_params.get("answered")
        questions = AnonymousQuestion.objects.filter(recipient=request.user)
        if answered == "true":
            questions = questions.filter(is_answered=True)
        elif answered == "false":
            questions = questions.filter(is_answered=False)
        questions = questions.order_by("-created_at")

        page = safe_int(request.query_params.get("page"), 1)
        page_size = safe_int(request.query_params.get("page_size"), 20)
        start = (page - 1) * page_size
        end = start + page_size
        total = questions.count()
        page_questions = questions[start:end]

        if request.user.is_staff:
            serializer = AdminQuestionSerializer(page_questions, many=True)
        else:
            serializer = QuestionSerializer(page_questions, many=True)
        return Response({
            "code": 0, "message": "success",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "results": serializer.data,
            }
        })


class AnswerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        inactive = ensure_plugin_active("question_box")
        if inactive:
            return inactive

        try:
            question = AnonymousQuestion.objects.get(pk=pk, recipient=request.user)
        except AnonymousQuestion.DoesNotExist:
            return Response(
                {"code": 1, "message": "问题不存在或无权限"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question.answer = serializer.validated_data["answer"]
        question.is_answered = True
        question.answered_at = timezone.now()
        question.save()

        return Response({"code": 0, "message": "success"})


class QuestionDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        inactive = ensure_plugin_active("question_box")
        if inactive:
            return inactive

        try:
            question = AnonymousQuestion.objects.get(pk=pk, recipient=request.user)
        except AnonymousQuestion.DoesNotExist:
            return Response(
                {"code": 1, "message": "问题不存在或无权限"},
                status=status.HTTP_404_NOT_FOUND,
            )
        question.delete()
        return Response({"code": 0, "message": "success"}, status=status.HTTP_200_OK)

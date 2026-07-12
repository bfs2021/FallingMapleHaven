from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.utils import api_response, safe_int
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Notification.objects.filter(recipient=request.user)
        unread_only = request.query_params.get("unread_only", "").lower() in ("1", "true")
        if unread_only:
            queryset = queryset.filter(is_read=False)

        page = safe_int(request.query_params.get("page"), 1)
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size
        total = queryset.count()
        page_notifications = queryset[start:end]

        serializer = NotificationSerializer(page_notifications, many=True)
        return api_response(
            data={
                "total": total,
                "page": page,
                "page_size": page_size,
                "results": serializer.data,
            }
        )


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return api_response(
                code=40004,
                message="通知不存在",
                data=None,
                status=status.HTTP_404_NOT_FOUND,
            )
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return api_response(message="已标记为已读")


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True
        )
        return api_response(message="已全部标记为已读")


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return api_response(data={"count": count})

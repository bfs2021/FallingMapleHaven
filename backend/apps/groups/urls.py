from django.urls import path
from apps.groups.views import (
    GroupListView,
    GroupCreateView,
    GroupDetailView,
    GroupUpdateView,
    GroupJoinView,
    GroupJoinRequestHandleView,
    GroupJoinRequestListView,
    GroupLeaveView,
    GroupMemberManageView,
    GroupPostsView,
    GroupDeleteView,
    GroupTransferView,
)

urlpatterns = [
    path("", GroupListView.as_view(), name="group-list"),
    path("create/", GroupCreateView.as_view(), name="group-create"),
    path("<int:pk>/", GroupDetailView.as_view(), name="group-detail"),
    path("<int:pk>/update/", GroupUpdateView.as_view(), name="group-update"),
    path("<int:pk>/join/", GroupJoinView.as_view(), name="group-join"),
    path("<int:pk>/leave/", GroupLeaveView.as_view(), name="group-leave"),
    path("<int:pk>/members/<int:user_id>/", GroupMemberManageView.as_view(), name="group-member-manage"),
    path("<int:pk>/posts/", GroupPostsView.as_view(), name="group-posts"),
    path("<int:pk>/delete/", GroupDeleteView.as_view(), name="group-delete"),
    path("<int:pk>/transfer/", GroupTransferView.as_view(), name="group-transfer"),
    path("<int:pk>/join-requests/", GroupJoinRequestListView.as_view(), name="group-join-requests"),
    path("<int:pk>/join-requests/<int:request_id>/handle/", GroupJoinRequestHandleView.as_view(), name="group-join-request-handle"),
]

from django.urls import path
from apps.profiles.views import (
    ProfileView, VisitorListView, UserPostListView,
    GuestbookListView, GuestbookCreateView, GuestbookReplyView, GuestbookDeleteView,
    ProfileAdminView,
)

urlpatterns = [
    path("<str:username_or_id>/", ProfileView.as_view(), name="profile-detail"),
    path("<str:username_or_id>/posts/", UserPostListView.as_view(), name="profile-posts"),
    path("<str:username_or_id>/visitors/", VisitorListView.as_view(), name="profile-visitors"),
    path("<str:username_or_id>/guestbook/", GuestbookListView.as_view(), name="guestbook-list"),
    path("<str:username_or_id>/guestbook/create/", GuestbookCreateView.as_view(), name="guestbook-create"),
    path("guestbook/<int:entry_id>/reply/", GuestbookReplyView.as_view(), name="guestbook-reply"),
    path("guestbook/<int:entry_id>/delete/", GuestbookDeleteView.as_view(), name="guestbook-delete"),
    path("<str:username_or_id>/admin/", ProfileAdminView.as_view(), name="profile-admin"),
]

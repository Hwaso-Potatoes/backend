from django.urls import path

from .views import FriendDeleteView, FriendRequestAcceptView, FriendRequestRejectView, FriendView, ReceivedFriendRequestView


urlpatterns = [
    path("", FriendView.as_view(), name="friend"),
    path("requests/", ReceivedFriendRequestView.as_view(), name="friend-request-received"),
    path("requests/<int:request_id>/accept/", FriendRequestAcceptView.as_view(), name="friend-request-accept"),
    path("requests/<int:request_id>/reject/", FriendRequestRejectView.as_view(), name="friend-request-reject"),
    path("<int:friend_id>/", FriendDeleteView.as_view(), name="friend-delete"),
]
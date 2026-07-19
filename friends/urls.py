from django.urls import path
from .views import FriendView, DeleteView, ReceivedView, RespondView


urlpatterns = [
    path("", FriendView.as_view(), name="friend"),
    path("requests/", ReceivedView.as_view(), name="friend-request-received"),
    path("requests/<int:request_id>/", RespondView.as_view(), name="friend-request-respond"),
    path("<int:friend_id>/", DeleteView.as_view(), name="friend-delete"),
]
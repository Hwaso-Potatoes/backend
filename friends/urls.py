from django.urls import path

from .views import (
    FriendDeleteView,
    FriendListView,
    FriendQRCreateView,
    FriendQRRedeemView,
)


urlpatterns = [
    path( "", FriendListView.as_view(), name="friend-list"),
    path("qr/", FriendQRCreateView.as_view(), name="friend-qr-create"),
    path("qr/redeem/", FriendQRRedeemView.as_view(), name="friend-qr-redeem"),
    path( "<int:friend_id>/", FriendDeleteView.as_view(), name="friend-delete"),
]
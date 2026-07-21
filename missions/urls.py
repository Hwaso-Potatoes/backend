from django.urls import path

from missions.views.badge import BadgeListView
from missions.views.accessory import AccessoryListView, AccessoryDetailView
from missions.views.mission import MissionListView


urlpatterns = [
    path("<int:pet_id>/badges/", BadgeListView.as_view(), name="pet-badge-list"),
    
    path("<int:pet_id>/missions/", MissionListView.as_view(), name="pet-mission-list"),

    path("<int:pet_id>/accessories/", AccessoryListView.as_view(), name="pet-accessory-list"),
    path("<int:pet_id>/accessories/<int:accessory_id>/", AccessoryDetailView.as_view(), name="pet-accessory-detail")
]
from django.urls import path

from missions.views.badge import PetBadgeListView
from missions.views.accessory import AccessoryEquipView, AccessoryUnequipView, PetAccessoryListView
from missions.views.mission import MissionListView, MissionClaimView


urlpatterns = [
    path("<int:pet_id>/badges/", PetBadgeListView.as_view(), name="pet-badge-list"),
    
    path("<int:pet_id>/missions/", MissionListView.as_view(), name="pet-mission-list"),
    path("<int:pet_id>/missions/<int:pet_mission_id>/claim/", MissionClaimView.as_view(), name="mission-claim"),

    path("<int:pet_id>/accessories/", PetAccessoryListView.as_view(), name="pet-accessory-list"),
    path("<int:pet_id>/accessories/<int:accessory_id>/equip/", AccessoryEquipView.as_view(), name="accessory-equip"),
    path("<int:pet_id>/accessories/<int:accessory_id>/unequip/", AccessoryUnequipView.as_view(), name="accessory-unequip"),
]
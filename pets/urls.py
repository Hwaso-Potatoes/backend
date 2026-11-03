from django.urls import path
from .views import PetListCreateView, PetDetailView, PetGrowthView

urlpatterns = [
    path("", PetListCreateView.as_view(), name="pet-list"),
    path("<int:pet_id>/", PetDetailView.as_view(), name="pet-detail"),
    path("<int:pet_id>/growth/", PetGrowthView.as_view(), name="pet-growth"),
]
from django.urls import path

from walk.reports.views import PetWalkReportView


urlpatterns = [
    path("<int:pet_id>/reports/", PetWalkReportView.as_view(), name="pet-walk-report"),
]
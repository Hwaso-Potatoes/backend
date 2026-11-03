from django.urls import path

from .views import AttendanceCalendarView, AttendanceRewardListView, AttendanceRewardOpenView, AttendanceSummaryView


urlpatterns = [
    path("summary/", AttendanceSummaryView.as_view(), name="attendance-summary"),
    path("calendar/", AttendanceCalendarView.as_view(), name="attendance-calendar"),
    path("rewards/", AttendanceRewardListView.as_view(), name="attendance-reward-list"),
    path("rewards/<int:reward_id>/open/", AttendanceRewardOpenView.as_view(), name="attendance-reward-open"),
]
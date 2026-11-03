from django.contrib import admin

from .models import (
    Attendance,
    AttendanceReward,
    AttendanceRewardDay,
)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "pet",
        "attendance_date",
        "created_at",
    )

    list_filter = (
        "attendance_date",
    )

    search_fields = (
        "user__email",
        "pet__name",
    )

    readonly_fields = (
        "created_at",
    )


@admin.register(AttendanceRewardDay)
class AttendanceRewardDayAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reward_date",
        "created_at",
    )

    list_filter = (
        "reward_date",
    )

    ordering = (
        "-reward_date",
    )

    readonly_fields = (
        "created_at",
    )


@admin.register(AttendanceReward)
class AttendanceRewardAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "attendance",
        "accessory",
        "opened",
        "created_at",
    )

    list_filter = (
        "opened",
        "created_at",
    )

    search_fields = (
        "attendance__user__email",
        "attendance__pet__name",
        "accessory__name",
    )

    readonly_fields = (
        "created_at",
        "opened_at",
    )
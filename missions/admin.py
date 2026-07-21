from django.contrib import admin
from .models import Accessory, Badge, Mission, PetAccessory, PetBadge, PetMission


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "image",
    )
    search_fields = ("name",)
    ordering = ("id",)


@admin.register(PetBadge)
class PetBadgeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pet",
        "badge",
        "acquired_at",
    )
    list_filter = ("badge",)
    search_fields = (
        "pet__name",
        "badge__name",
    )
    list_select_related = (
        "pet",
        "badge",
    )
    ordering = ("-acquired_at",)


@admin.register(Accessory)
class AccessoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "image",
    )
    search_fields = ("name",)
    ordering = ("id",)


@admin.register(PetAccessory)
class PetAccessoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pet",
        "accessory",
        "is_equipped",
        "acquired_at",
    )
    list_filter = (
        "is_equipped",
        "accessory",
    )
    search_fields = (
        "pet__name",
        "accessory__name",
    )
    list_select_related = (
        "pet",
        "accessory",
    )
    ordering = (
        "-is_equipped",
        "-acquired_at",
    )


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "period",
        "mission_type",
        "goal",
        "required_count",
        "reward_experience",
        "reward_badge",
        "reward_accessory",
    )
    list_filter = (
        "period",
        "mission_type",
    )
    search_fields = (
        "title",
        "reward_badge__name",
        "reward_accessory__name",
    )
    list_select_related = (
        "reward_badge",
        "reward_accessory",
    )
    ordering = (
        "period",
        "id",
    )


@admin.register(PetMission)
class PetMissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pet",
        "mission",
        "period_start",
        "period_end",
        "current_value",
        "current_count",
        "status",
        "completed_at",
        "claimed_at",
    )
    list_filter = (
        "status",
        "mission__period",
        "period_start",
    )
    search_fields = (
        "pet__name",
        "mission__title",
    )
    list_select_related = (
        "pet",
        "mission",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = (
        "-period_start",
        "pet",
        "mission",
    )
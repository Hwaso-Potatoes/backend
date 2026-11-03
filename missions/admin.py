from django.contrib import admin

from missions.models import Accessory, Badge, Mission, PetAccessory, PetBadge, PetMission


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "period",
        "mission_type",
        "goal",
        "required_count",
    )
    list_filter = (
        "period",
        "mission_type",
    )
    search_fields = (
        "title",
    )


@admin.register(PetMission)
class PetMissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pet",
        "mission",
        "current_value",
        "current_count",
        "status",
        "period_start",
        "period_end",
    )
    list_filter = (
        "status",
        "mission__period",
    )
    search_fields = (
        "pet__name",
        "mission__title",
    )


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "condition_type",
        "goal",
    )
    list_filter = (
        "condition_type",
    )
    search_fields = (
        "name",
    )


@admin.register(PetBadge)
class PetBadgeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pet",
        "badge",
        "acquired_at",
    )
    search_fields = (
        "pet__name",
        "badge__name",
    )


@admin.register(Accessory)
class AccessoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "category",
    )
    list_filter = (
        "category",
    )
    search_fields = (
        "name",
    )


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
        "accessory__category",
    )
    search_fields = (
        "pet__name",
        "accessory__name",
    )
from django.contrib import admin

from pets.models import PetHistory


@admin.register(PetHistory)
class PetHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pet",
        "before_level",
        "after_level",
        "created_at",
    )
    list_filter = ("before_level", "after_level")
    search_fields = ("pet__name",)
    readonly_fields = ("created_at",)
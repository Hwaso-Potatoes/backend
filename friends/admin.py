from django.contrib import admin

from .models import Friend


@admin.register(Friend)
class FriendAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "requester",
        "receiver",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "status",
        "created_at",
    )
    search_fields = (
        "requester__email",
        "requester__nickname",
        "receiver__email",
        "receiver__nickname",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
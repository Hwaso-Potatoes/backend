from django.contrib import admin

from .models import Friend


@admin.register(Friend)
class FriendAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user1",
        "user2",
        "created_at",
    )

    search_fields = (
        "user1__email",
        "user1__nickname",
        "user2__email",
        "user2__nickname",
    )

    readonly_fields = (
        "created_at",
    )

    list_select_related = (
        "user1",
        "user2",
    )

    ordering = ("-created_at",)
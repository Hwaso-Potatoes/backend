from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Friend(models.Model):
    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_as_user1",
    )
    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_as_user2",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(user1_id__lt=F("user2_id")),
                name="friend_user_order",
            ),
            models.UniqueConstraint(
                fields=["user1", "user2"],
                name="unique_friendship",
            ),
        ]
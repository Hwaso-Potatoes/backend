from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Friend(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "대기"
        ACCEPTED = "ACCEPTED", "수락"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_friend_requests",
        verbose_name="요청자",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_friend_requests",
        verbose_name="수신자",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="상태",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="생성일",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="수정일",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(requester=F("receiver")),
                name="prevent_self_friend_request",
            ),
            models.UniqueConstraint(
                fields=["requester", "receiver"],
                name="unique_friend_request",
            ),
        ]

    def __str__(self):
        return (
            f"{self.requester.nickname} → "
            f"{self.receiver.nickname} ({self.status})"
        )
from datetime import time

from django.conf import settings
from django.db import models


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )

    allow_all = models.BooleanField(default=True)

    walk_reminder = models.BooleanField(default=True)
    walk_reminder_time = models.TimeField(default=time(18, 0))
    walk_report = models.BooleanField(default=True)
    last_walk_reminder_sent_date = models.DateField(null=True, blank=True)

    level_badge = models.BooleanField(default=True)
    accessory = models.BooleanField(default=True)

    friend_walk = models.BooleanField(default=True)

    marketing = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} 알림 설정"


class DeviceToken(models.Model):
    class Platform(models.TextChoices):
        ANDROID = "ANDROID", "Android"
        IOS = "IOS", "iOS"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens",
    )

    token = models.CharField(
        max_length=512,
        unique=True,
    )

    platform = models.CharField(
        max_length=10,
        choices=Platform.choices,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.platform}"


class NotificationCampaign(models.Model):
    title = models.CharField(
        "제목",
        max_length=100,
    )

    body = models.CharField(
        "내용",
        max_length=255,
    )

    data = models.JSONField(
        "추가 데이터",
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
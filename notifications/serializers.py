from rest_framework import serializers

from .models import DeviceToken, NotificationPreference


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = (
            "allow_all",
            "walk_reminder",
            "walk_reminder_time",
            "walk_report",
            "level_badge",
            "accessory",
            "friend_walk",
            "marketing",
        )


class DeviceTokenRegisterSerializer(serializers.Serializer):
    token = serializers.CharField(
        max_length=512,
    )

    platform = serializers.ChoiceField(
        choices=DeviceToken.Platform.choices,
        required=False,
        allow_blank=True,
    )


class DeviceTokenUnregisterSerializer(serializers.Serializer):
    token = serializers.CharField(
        max_length=512,
    )
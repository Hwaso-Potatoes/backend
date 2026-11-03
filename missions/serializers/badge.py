from rest_framework import serializers

from missions.models import Badge, PetBadge


class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = (
            "id",
            "name",
            "image",
            "description",
        )
        read_only_fields = fields


class PetBadgeListSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(
        read_only=True,
    )

    class Meta:
        model = PetBadge
        fields = (
            "badge",
            "acquired_at",
        )
        read_only_fields = fields
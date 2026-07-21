from rest_framework import serializers

from missions.models import PetBadge


class BadgeListSerializer(serializers.ModelSerializer):
    badge_id = serializers.IntegerField(
        source="badge.id",
        read_only=True,
    )
    badge_name = serializers.CharField(
        source="badge.name",
        read_only=True,
    )
    badge_image = serializers.ImageField(
        source="badge.image",
        read_only=True,
    )

    class Meta:
        model = PetBadge
        fields = (
            "badge_id",
            "badge_name",
            "badge_image",
            "acquired_at",
        )
        read_only_fields = fields
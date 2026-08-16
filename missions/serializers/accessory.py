from rest_framework import serializers

from missions.models import Accessory, PetAccessory


class AccessorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Accessory
        fields = (
            "id",
            "name",
            "image",
            "category",
        )
        read_only_fields = fields


class PetAccessoryListSerializer(serializers.ModelSerializer):
    accessory = AccessorySerializer(
        read_only=True,
    )

    class Meta:
        model = PetAccessory
        fields = (
            "id",
            "accessory",
            "is_equipped",
            "acquired_at",
        )
        read_only_fields = fields


class AccessoryEquipResultSerializer(serializers.ModelSerializer):
    accessory = AccessorySerializer(
        read_only=True,
    )

    class Meta:
        model = PetAccessory
        fields = (
            "id",
            "accessory",
            "is_equipped",
        )
        read_only_fields = fields
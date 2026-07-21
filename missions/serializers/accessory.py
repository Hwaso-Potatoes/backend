from rest_framework import serializers

from missions.models import PetAccessory


class AccessoryListSerializer(serializers.ModelSerializer):
    pet_accessory_id = serializers.IntegerField(
        source="id",
        read_only=True,
    )
    accessory_id = serializers.IntegerField(
        source="accessory.id",
        read_only=True,
    )
    accessory_name = serializers.CharField(
        source="accessory.name",
        read_only=True,
    )
    accessory_image = serializers.ImageField(
        source="accessory.image",
        read_only=True,
    )

    class Meta:
        model = PetAccessory
        fields = (
            "pet_accessory_id",
            "accessory_id",
            "accessory_name",
            "accessory_image",
            "is_equipped",
            "acquired_at",
        )
        read_only_fields = fields


class AccessoryEquipSerializer(serializers.Serializer):
    is_equipped = serializers.BooleanField()


class AccessoryEquipResultSerializer(serializers.ModelSerializer):
    pet_accessory_id = serializers.IntegerField(
        source="id",
        read_only=True,
    )
    accessory_id = serializers.IntegerField(
        source="accessory.id",
        read_only=True,
    )
    accessory_name = serializers.CharField(
        source="accessory.name",
        read_only=True,
    )
    accessory_image = serializers.ImageField(
        source="accessory.image",
        read_only=True,
    )

    class Meta:
        model = PetAccessory
        fields = (
            "pet_accessory_id",
            "accessory_id",
            "accessory_name",
            "accessory_image",
            "is_equipped",
        )
        read_only_fields = fields
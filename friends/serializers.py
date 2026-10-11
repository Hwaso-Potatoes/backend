from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from pets.models import Pet
from walk.models import WalkingSession


User = get_user_model()


class FriendAccessorySerializer(serializers.Serializer):
    id = serializers.IntegerField(
        source="accessory.id",
        read_only=True,
    )
    name = serializers.CharField(
        source="accessory.name",
        read_only=True,
    )
    image = serializers.ImageField(
        source="accessory.image",
        read_only=True,
    )
    category = serializers.CharField(
        source="accessory.category",
        read_only=True,
    )


class FriendRecentWalkSerializer(serializers.Serializer):
    status = serializers.CharField(read_only=True)
    start_time = serializers.DateTimeField(read_only=True)
    end_time = serializers.DateTimeField(
        read_only=True,
        allow_null=True,
    )


# 친구의 반려견 정보
class FriendPetSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    is_walking = serializers.SerializerMethodField()
    recent_walk = serializers.SerializerMethodField()
    equipped_accessories = serializers.SerializerMethodField()

    class Meta:
        model = Pet
        fields = (
            "id",
            "name",
            "breed",
            "age",
            "personalities",
            "is_walking",
            "recent_walk",
            "equipped_accessories",
        )
        read_only_fields = fields

    def get_age(self, obj):
        if not obj.birth_date:
            return None

        today = timezone.localdate()

        age = today.year - obj.birth_date.year

        if (
            today.month,
            today.day,
        ) < (
            obj.birth_date.month,
            obj.birth_date.day,
        ):
            age -= 1

        return age

    def get_is_walking(self, obj):
        if hasattr(obj, "is_walking"):
            return obj.is_walking

        return obj.walking_sessions.filter(
            status__in=[
                "WALKING",
                "PAUSED",
            ],
        ).exists()

    @extend_schema_field(
        FriendRecentWalkSerializer(
            allow_null=True,
        )
    )
    def get_recent_walk(self, obj):
        if hasattr(obj, "recent_walk_status"):
            if obj.recent_walk_status is None:
                return None

            return {
                "status": obj.recent_walk_status,
                "start_time": obj.recent_walk_start_time,
                "end_time": obj.recent_walk_end_time,
            }

        recent_walk = (
            obj.walking_sessions
            .order_by(
                "-start_time",
                "-id",
            )
            .first()
        )

        if not recent_walk:
            return None

        return {
            "status": recent_walk.status,
            "start_time": recent_walk.start_time,
            "end_time": recent_walk.end_time,
        }

    def get_equipped_accessories(self, obj):
        equipped = getattr(
            obj,
            "equipped_accessories",
            None,
        )

        if equipped is None:
            equipped = (
                obj.pet_accessories
                .filter(
                    is_equipped=True,
                )
                .select_related("accessory")
            )

        return FriendAccessorySerializer(
            equipped,
            many=True,
            context=self.context,
        ).data


# 친구 정보
class FriendListSerializer(serializers.ModelSerializer):
    pets = FriendPetSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "nickname",
            "pets",
        )
        read_only_fields = fields


# QR invite token 생성 응답
class FriendQRCreateResultSerializer(serializers.Serializer):
    token = serializers.CharField(read_only=True)
    expires_in = serializers.IntegerField(read_only=True)


# QR 스캔 후 token 입력
class FriendQRRedeemSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)


# 친구 추가 성공 응답
class FriendQRRedeemResultSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    friend = FriendListSerializer(read_only=True)
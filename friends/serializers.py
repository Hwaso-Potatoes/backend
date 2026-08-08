from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers

from .models import Friend
from pets.models import Pet


User = get_user_model()


# 친구 요청
class FriendRequestCreateSerializer(serializers.ModelSerializer):
    receiver_id = serializers.PrimaryKeyRelatedField(
        source="receiver",
        queryset=User.objects.filter(is_active=True),
    )

    class Meta:
        model = Friend
        fields = ("receiver_id",)

    def validate_receiver_id(self, receiver):
        requester = self.context["request"].user

        if requester == receiver:
            raise serializers.ValidationError("자기 자신에게 친구 요청을 보낼 수 없습니다.")

        relationship_exists = Friend.objects.filter(
            Q(requester=requester, receiver=receiver)
            | Q(requester=receiver, receiver=requester)
        ).exists()

        if relationship_exists:
            raise serializers.ValidationError("이미 친구 관계이거나 처리 중인 친구 요청이 있습니다.")

        return receiver

    def create(self, validated_data):
        return Friend.objects.create(
            requester=self.context["request"].user,
            **validated_data,
        )


# 친구 요청 후 결과 반환
class FriendRequestCreateResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Friend
        fields = ("id",)


# 내가 받은 친구 요청 목록 반환 시, 요청자의 정보 반환
class FriendRequesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "nickname",
        )
        read_only_fields = fields


# 내가 받은 친구 요청 목록 반환
class ReceivedFriendRequestSerializer(serializers.ModelSerializer):
    requester = FriendRequesterSerializer(
        read_only=True,
    )

    class Meta:
        model = Friend
        fields = (
            "id",
            "requester",
        )
        read_only_fields = fields


# 나의 친구 정보 반환 시, 친구의 반려견 정보 반환
class FriendPetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = (
            "id",
            "name",
            "breed",
        )
        read_only_fields = fields


# 나의 친구 정보 반환
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
            "pets"
        )
        read_only_fields = fields
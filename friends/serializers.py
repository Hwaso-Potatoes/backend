from django.contrib.auth import get_user_model
from rest_framework import serializers

from pets.models import Pet


User = get_user_model()


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
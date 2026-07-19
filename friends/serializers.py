from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers

from .models import Friend


User = get_user_model()


class CreateSerializer(serializers.ModelSerializer):
    receiver_id = serializers.PrimaryKeyRelatedField(
        source="receiver",
        queryset=User.objects.filter(is_active=True),
    )

    class Meta:
        model = Friend
        fields = (
            "receiver_id",
        )

    def validate_receiver_id(self, receiver):
        requester = self.context["request"].user

        if requester == receiver:
            raise serializers.ValidationError(
                "자기 자신에게 친구 요청을 보낼 수 없습니다."
            )

        relationship_exists = Friend.objects.filter(
            Q(
                requester=requester,
                receiver=receiver,
            )
            | Q(
                requester=receiver,
                receiver=requester,
            )
        ).exists()

        if relationship_exists:
            raise serializers.ValidationError(
                "이미 친구 관계이거나 처리 중인 친구 요청이 있습니다."
            )

        return receiver

    def create(self, validated_data):
        return Friend.objects.create(
            requester=self.context["request"].user,
            **validated_data,
        )


class CreateResultSerializer(serializers.ModelSerializer):
    request_id = serializers.IntegerField(
        source="id",
        read_only=True,
    )

    class Meta:
        model = Friend
        fields = (
            "request_id",
        )
        read_only_fields = fields


class ReceivedSerializer(serializers.ModelSerializer):
    request_id = serializers.IntegerField(
        source="id",
        read_only=True,
    )
    requester_id = serializers.IntegerField(
        source="requester.id",
        read_only=True,
    )
    requester_nickname = serializers.CharField(
        source="requester.nickname",
        read_only=True,
    )

    class Meta:
        model = Friend
        fields = (
            "request_id",
            "requester_id",
            "requester_nickname",
        )
        read_only_fields = fields


class RespondSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=(
            ("accept", "수락"),
            ("reject", "거절"),
        ),
    )


class ListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "nickname",
        )
        read_only_fields = fields
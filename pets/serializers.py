from rest_framework import serializers
from .models import Pet, PERSONALITY_CHOICES


from django.db import transaction
from rest_framework import serializers

from .models import Pet, PERSONALITY_CHOICES


class PetSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(
        write_only=True,
        max_length=8,
        required=False,
        allow_blank=False,
    )

    personalities = serializers.ListField(
        child=serializers.ChoiceField(
            choices=PERSONALITY_CHOICES
        ),
        required=False,
    )

    class Meta:
        model = Pet
        fields = [
            "id",
            "nickname",
            "name",
            "breed",
            "birth_date",
            "profile_image",
            "personalities",
            "level",
            "experience",
        ]

        read_only_fields = [
            "id",
            "level",
            "experience",
        ]

    def validate(self, attrs):
        request = self.context.get("request")

        if (
            self.instance is None
            and request
            and not request.user.nickname
            and not attrs.get("nickname")
        ):
            raise serializers.ValidationError(
                {
                    "nickname": "반려인 이름을 입력해 주세요."
                }
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        nickname = validated_data.pop(
            "nickname",
            None,
        )

        user = validated_data["user"]

        if nickname is not None:
            user.nickname = nickname
            user.save(
                update_fields=["nickname"]
            )

        return Pet.objects.create(
            **validated_data
        )

class PetGrowthSerializer(serializers.ModelSerializer):
    required_experience = serializers.SerializerMethodField()
    remaining_experience = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Pet
        fields = (
            "id",
            "level",
            "experience",
            "required_experience",
            "remaining_experience",
            "progress_percent",
        )
        read_only_fields = fields

    def get_required_experience(self, obj):
        return obj.level * 100

    def get_remaining_experience(self, obj):
        required_experience = self.get_required_experience(obj)

        return max(
            0,
            required_experience - obj.experience,
        )

    def get_progress_percent(self, obj):
        required_experience = self.get_required_experience(obj)

        if required_experience <= 0:
            return 0

        return min(
            100,
            int(obj.experience / required_experience * 100),
        )
    
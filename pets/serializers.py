from rest_framework import serializers
from .models import Pet, PERSONALITY_CHOICES


class PetSerializer(serializers.ModelSerializer):
    personalities = serializers.ListField(
        child=serializers.ChoiceField(choices=PERSONALITY_CHOICES),
        required=False,
    )
    class Meta:
        model = Pet
        fields = ["id", "name", "breed", "birth_date", "profile_image",
                   "personalities",  
                  "level", "experience", ]
        read_only_fields = ["id", "level", "experience"]

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
    
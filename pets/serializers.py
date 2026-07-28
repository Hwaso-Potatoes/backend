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
from rest_framework import serializers
from .models import Pet


class PetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = ["id", "name", "breed", "birth_date", "profile_image",
                  "level", "experience", "created_at", "updated_at"]
        read_only_fields = ["id", "level", "experience", "created_at", "updated_at"]
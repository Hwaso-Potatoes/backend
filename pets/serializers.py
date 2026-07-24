from rest_framework import serializers
from .models import Dog


class DogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dog
        fields = ["id", "name", "breed", "birth_date", "created_at"]
        read_only_fields = ["id", "created_at"]
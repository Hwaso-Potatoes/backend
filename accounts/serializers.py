from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """회원가입: 비밀번호 확인 + 검증 포함"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "nickname", "password", "password2"]

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError({"password2": "비밀번호가 일치하지 않습니다."})
        return data

    def create(self, validated_data):
        validated_data.pop("password2")
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            nickname=validated_data.get("nickname", ""),
        )


class UserSerializer(serializers.ModelSerializer):
    """내 프로필 조회/수정"""
    class Meta:
        model = User
        fields = ["id", "email", "nickname", "date_joined"]
        read_only_fields = ["id", "email", "date_joined"]

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
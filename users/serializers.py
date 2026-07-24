from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "nickname", "password", "password2"]
        read_only_fields = ["id",]

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")
        return data

    def create(self, validated_data):
        validated_data.pop("password2")

        return User.objects.create_user(
            email=validated_data["email"],
            nickname=validated_data["nickname"],
            password=validated_data["password"],
        )
    

class DetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "nickname"]
        read_only_fields = fields


class UpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["nickname"]


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_refresh(self, value):
        try:
            self.refresh_token = RefreshToken(value)
        except TokenError as error:
            raise serializers.ValidationError("Refresh Token이 만료되었습니다.") from error

        return value

    def save(self, **kwargs):
        self.refresh_token.blacklist()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
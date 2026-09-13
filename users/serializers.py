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
        fields = ["id", "email", "password", "password2"]
        read_only_fields = ["id",]

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")
        return data

    def create(self, validated_data):
        validated_data.pop("password2")

        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )
    

class DetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "nickname"]
        read_only_fields = fields


class UpdateSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(max_length=8, allow_blank=False)

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


class PasswordChangeSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "새 비밀번호가 일치하지 않습니다."})
        return data
    
class EmailChangeRequestSerializer(serializers.Serializer):
    """이메일 변경 1단계 — 새 이메일로 인증번호 발송"""
    email = serializers.EmailField()

    def validate_email(self, value):
        value = value.lower().strip()
        user = self.context["request"].user

        if value == (user.email or "").lower():
            raise serializers.ValidationError("현재 사용 중인 이메일과 동일합니다.")

        if User.objects.exclude(pk=user.pk).filter(email__iexact=value).exists():
            raise serializers.ValidationError("이미 사용 중인 이메일입니다.")

        return value


class EmailChangeConfirmSerializer(serializers.Serializer):
    """이메일 변경 2단계 — 인증번호 검증"""
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_email(self, value):
        return value.lower().strip()

class SocialLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField(required=False, help_text="kakao/google용")
    identity_token = serializers.CharField(required=False, help_text="apple용")
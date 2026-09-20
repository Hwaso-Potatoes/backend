from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from .services.verification import SignupVerificationTokenError, delete_signup_verification_token, validate_signup_verification_token

User = get_user_model()


# 회원가입
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )

    password2 = serializers.CharField(
        write_only=True,
    )

    verification_token = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "password2",
            "verification_token",
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError(
                {
                    "password2": "비밀번호가 일치하지 않습니다.",
                }
            )

        email = data["email"].lower().strip()
        verification_token = data["verification_token"]

        try:
            validate_signup_verification_token(
                email,
                verification_token,
            )

        except SignupVerificationTokenError as error:
            raise serializers.ValidationError(
                {
                    "verification_token": str(error),
                }
            ) from error

        data["email"] = email

        return data

    def create(self, validated_data):
        validated_data.pop("password2")

        verification_token = validated_data.pop(
            "verification_token"
        )

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )

        delete_signup_verification_token(
            verification_token
        )

        return user
    

# 사용자 프로필 조회
class DetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "nickname"]
        read_only_fields = fields


# 사용자 프로필 수정
class UpdateSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(max_length=8, allow_blank=False)

    class Meta:
        model = User
        fields = ["nickname"]


# 로그아웃
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


# 비밀번호 재설정(로그인시)
class PasswordChangeSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "새 비밀번호가 일치하지 않습니다."})
        return data


# 이메일 재설정 요청
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


# 이메일 재설정
class EmailChangeConfirmSerializer(serializers.Serializer):
    """이메일 변경 2단계 — 인증번호 검증"""
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_email(self, value):
        return value.lower().strip()


# 소셜 로그인
class SocialLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField(required=False, help_text="kakao/google용")
    identity_token = serializers.CharField(required=False, help_text="apple용")


# 이메일 인증 요청
class RegisterEmailRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        email = value.lower().strip()

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("이미 가입된 이메일입니다.")

        return email


# 이메일 인증
class RegisterEmailVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()

    def validate_email(self, value):
        return value.lower().strip()

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("인증번호는 6자리 숫자여야 합니다.")

        return value


# 비밀번호 재설정 요청(비로그인시)
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower().strip()


# 비밀번호 재설정(비로그인시)
class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )

    new_password2 = serializers.CharField(
        write_only=True,
    )

    def validate(self, data):
        if data["new_password"] != data["new_password2"]:
            raise serializers.ValidationError(
                {
                    "new_password2": "비밀번호가 일치하지 않습니다."
                }
            )

        return data
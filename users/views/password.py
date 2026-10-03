import secrets
import string

from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from ..models import EmailVerification
from ..serializers import (
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)
from ..utils import send_password_reset_code, send_temporary_password


User = get_user_model()


# 비밀번호 재설정(로그인시)
class PasswordResetView(APIView):
    """비밀번호 재설정 (새 비밀번호 두 번 입력)"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["사용자"],
        summary="비밀번호 재설정(로그인 후)",
        description="환경설정 > 비밀번호 재설정 화면에서 새 비밀번호를 두 번 입력해 변경합니다.",
        request=PasswordChangeSerializer,
        responses={
            200: inline_serializer(
                name="PasswordChangeResponse",
                fields={
                    "detail": serializers.CharField(),
                },
            ),
            400: OpenApiResponse(description="비밀번호 불일치 / 비밀번호 규칙 위반"),
            401: OpenApiResponse(description="인증 실패"),
        },
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"detail": "비밀번호가 변경되었습니다."})


TEMPORARY_PASSWORD_LENGTH = 12


def generate_temporary_password():
    """영문 대/소문자 + 숫자를 각각 1개 이상 포함한 임시 비밀번호"""
    alphabet = string.ascii_letters + string.digits

    while True:
        password = "".join(
            secrets.choice(alphabet) for _ in range(TEMPORARY_PASSWORD_LENGTH)
        )

        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
        ):
            return password


class PasswordResetRequestView(APIView):
    """비밀번호 재설정 1단계 — 가입된 이메일로 인증번호 발송"""
    permission_classes = [permissions.AllowAny]
    throttle_scope = "email_verify"

    @extend_schema(
        tags=["인증"],
        summary="비밀번호 재설정 요청",
        description=(
            "가입된 이메일로 6자리 인증번호를 발송합니다. "
            "계정 존재 여부를 노출하지 않기 위해, 가입되지 않은 이메일에도 동일한 응답을 반환합니다."
        ),
        request=PasswordResetRequestSerializer,
        responses={
            200: inline_serializer(
                name="PasswordResetRequestResponse",
                fields={
                    "detail": serializers.CharField(),
                    "expires_in": serializers.IntegerField(),
                },
            ),
            400: OpenApiResponse(description="잘못된 요청"),
            429: OpenApiResponse(description="재발송 쿨다운"),
            503: OpenApiResponse(description="이메일 발송 실패"),
        },
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()

        # 가입된 이메일일 때만 실제로 발송 (응답은 동일)
        if user is not None:
            remaining = EmailVerification.cooldown_remaining(
                user=user,
                purpose=EmailVerification.Purpose.PASSWORD_RESET,
            )

            if remaining:
                return Response(
                    {
                        "detail": f"{remaining}초 후에 다시 요청해 주세요.",
                        "retry_after": remaining,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            verification, code = EmailVerification.issue(
                user=user,
                email=email,
                purpose=EmailVerification.Purpose.PASSWORD_RESET,
            )

            try:
                send_password_reset_code(
                    email,
                    code,
                    EmailVerification.CODE_TTL_MINUTES,
                )
            except Exception:
                # 발송 실패 시 쿨다운에 걸리지 않도록 발급 내역 삭제
                verification.delete()

                return Response(
                    {
                        "detail": "인증번호 발송에 실패했습니다. 다시 시도해 주세요.",
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        return Response(
            {
                "detail": "인증번호를 발송했습니다.",
                "expires_in": EmailVerification.CODE_TTL_MINUTES * 60,
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """비밀번호 재설정 2단계 — 인증번호 확인 후 임시 비밀번호 발급"""
    permission_classes = [permissions.AllowAny]
    throttle_scope = "email_verify"

    @extend_schema(
        tags=["인증"],
        summary="비밀번호 재설정 인증",
        description="인증번호를 확인하고 임시 비밀번호를 메일로 발송합니다. 기존 로그인 세션은 모두 무효화됩니다.",
        request=PasswordResetConfirmSerializer,
        responses={
            200: inline_serializer(
                name="PasswordResetConfirmResponse",
                fields={
                    "detail": serializers.CharField(),
                },
            ),
            400: OpenApiResponse(description="인증번호 불일치 / 만료 / 시도 초과"),
            503: OpenApiResponse(description="이메일 발송 실패"),
        },
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        no_request_response = Response(
            {"detail": "인증 요청 내역이 없습니다. 다시 요청해 주세요."},
            status=status.HTTP_400_BAD_REQUEST,
        )

        user = User.objects.filter(email__iexact=email).first()

        # 가입 여부를 노출하지 않도록 요청 내역이 없을 때와 같은 응답
        if user is None:
            return no_request_response

        verification = (
            EmailVerification.objects.filter(
                user=user,
                email=email,
                purpose=EmailVerification.Purpose.PASSWORD_RESET,
                verified_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )

        if verification is None:
            return no_request_response

        if verification.is_expired:
            return Response(
                {"detail": "인증번호가 만료되었습니다. 다시 요청해 주세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification.attempt_count >= EmailVerification.MAX_ATTEMPTS:
            return Response(
                {"detail": "시도 횟수를 초과했습니다. 다시 요청해 주세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not verification.verify(code):
            return Response(
                {
                    "detail": "인증번호가 일치하지 않습니다.",
                    "attempts_left": EmailVerification.MAX_ATTEMPTS - verification.attempt_count,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        temporary_password = generate_temporary_password()

        try:
            with transaction.atomic():
                user.set_password(temporary_password)
                user.save(update_fields=["password", "updated_at"])

                # 기존 세션 전부 무효화
                for outstanding_token in OutstandingToken.objects.filter(user=user):
                    BlacklistedToken.objects.get_or_create(token=outstanding_token)

                # 메일 발송에 실패하면 비밀번호 변경까지 롤백 (임시 비밀번호를 모르는 채로 잠기는 것 방지)
                send_temporary_password(email, temporary_password)
        except Exception:
            return Response(
                {"detail": "임시 비밀번호 발송에 실패했습니다. 인증번호를 다시 요청해 주세요."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "detail": "임시 비밀번호를 메일로 발송했습니다.",
            },
            status=status.HTTP_200_OK,
        )
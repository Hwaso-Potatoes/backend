from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import EmailVerification
from ..serializers import (
    EmailChangeConfirmSerializer,
    EmailChangeRequestSerializer,
    RegisterEmailRequestSerializer,
    RegisterEmailVerifySerializer,
)
from ..services.verification import (
    CODE_TTL_SECONDS,
    SignupCodeCooldownError,
    SignupCodeVerificationError,
    clear_signup_code,
    issue_signup_code,
    verify_signup_code,
)
from ..utils import send_signup_verification_code, send_verification_code


User = get_user_model()


# 이메일 변경 요청
class EmailChangeView(APIView):
    """이메일 변경 1단계 — 새 이메일로 인증번호 발송"""
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "email_verify"

    @extend_schema(
        tags=["사용자"],
        summary="이메일 변경 요청",
        description="새 이메일로 6자리 인증번호를 발송합니다. 이 단계에서는 이메일이 변경되지 않습니다.",
        request=EmailChangeRequestSerializer,
        responses={
            200: inline_serializer(
                name="EmailChangeRequestResponse",
                fields={
                    "detail": serializers.CharField(),
                    "expires_in": serializers.IntegerField(),
                },
            ),
            400: OpenApiResponse(description="잘못된 요청"),
            401: OpenApiResponse(description="인증 실패"),
            429: OpenApiResponse(description="재발송 쿨다운"),
        },
    )
    def post(self, request):
        serializer = EmailChangeRequestSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        new_email = serializer.validated_data["email"]

        remaining = EmailVerification.cooldown_remaining(
            user=request.user,
            purpose=EmailVerification.Purpose.EMAIL_CHANGE,
        )

        if remaining:
            return Response(
                {
                    "detail": f"{remaining}초 후에 다시 요청해 주세요.",
                    "retry_after": remaining,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        _, code = EmailVerification.issue(
            user=request.user,
            email=new_email,
            purpose=EmailVerification.Purpose.EMAIL_CHANGE,
        )

        send_verification_code(
            new_email,
            code,
            EmailVerification.CODE_TTL_MINUTES,
        )

        return Response(
            {
                "detail": "인증번호를 발송했습니다.",
                "expires_in": EmailVerification.CODE_TTL_MINUTES * 60,
            },
            status=status.HTTP_200_OK,
        )


# 이메일 변경
class EmailChangeVerifyView(APIView):
    """이메일 변경 2단계 — 인증번호 확인 후 변경 확정"""
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "email_verify"

    @extend_schema(
        tags=["사용자"],
        summary="이메일 변경 인증",
        description="발송된 인증번호를 확인하고 이메일 변경을 확정합니다.",
        request=EmailChangeConfirmSerializer,
        responses={
            200: inline_serializer(
                name="EmailChangeVerifyResponse",
                fields={
                    "detail": serializers.CharField(),
                    "email": serializers.EmailField(),
                },
            ),
            400: OpenApiResponse(description="인증번호 불일치 / 만료"),
            401: OpenApiResponse(description="인증 실패"),
            409: OpenApiResponse(description="이미 사용 중인 이메일"),
        },
    )
    def post(self, request):
        serializer = EmailChangeConfirmSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        new_email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]
        user = request.user

        verification = (
            EmailVerification.objects.filter(
                user=user,
                email=new_email,
                purpose=EmailVerification.Purpose.EMAIL_CHANGE,
                verified_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )

        if verification is None:
            return Response(
                {
                    "detail": "인증 요청 내역이 없습니다. 다시 요청해 주세요."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification.is_expired:
            return Response(
                {
                    "detail": "인증번호가 만료되었습니다. 다시 요청해 주세요."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification.attempt_count >= EmailVerification.MAX_ATTEMPTS:
            return Response(
                {
                    "detail": "시도 횟수를 초과했습니다. 다시 요청해 주세요."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not verification.verify(code):
            return Response(
                {
                    "detail": "인증번호가 일치하지 않습니다.",
                    "attempts_left": (
                        EmailVerification.MAX_ATTEMPTS
                        - verification.attempt_count
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            if (
                User.objects
                .exclude(pk=user.pk)
                .filter(email__iexact=new_email)
                .exists()
            ):
                return Response(
                    {
                        "detail": "이미 사용 중인 이메일입니다."
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            user.email = new_email
            user.save(
                update_fields=["email", "updated_at"]
            )

        return Response(
            {
                "detail": "이메일이 변경되었습니다.",
                "email": user.email,
            },
            status=status.HTTP_200_OK,
        )


# 회원가입시 이메일 인증번호 발송
class RegisterEmailRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["인증"],
        summary="회원가입 이메일 인증번호 발송",
        description="회원가입할 이메일로 6자리 인증번호를 발송합니다.",
        request=RegisterEmailRequestSerializer,
        responses={
            200: inline_serializer(
                name="RegisterEmailRequestResponse",
                fields={
                    "detail": serializers.CharField(),
                    "expires_in": serializers.IntegerField(),
                },
            ),
            400: OpenApiResponse(description="잘못된 요청"),
            429: OpenApiResponse(description="재발송 제한"),
            503: OpenApiResponse(description="이메일 발송 실패"),
        },
    )
    def post(self, request):
        serializer = RegisterEmailRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            code = issue_signup_code(email)

        except SignupCodeCooldownError as error:
            return Response(
                {
                    "detail": f"{error.retry_after}초 후에 다시 요청해 주세요.",
                    "retry_after": error.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            send_signup_verification_code(
                email,
                code,
                CODE_TTL_SECONDS // 60,
            )

        except Exception:
            clear_signup_code(email)

            return Response(
                {
                    "detail": "인증번호 발송에 실패했습니다. 다시 시도해 주세요.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "detail": "인증번호를 발송했습니다.",
                "expires_in": CODE_TTL_SECONDS,
            },
            status=status.HTTP_200_OK,
        )


# 회원가입시 이메일 인증번호 확인
class RegisterEmailVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["인증"],
        summary="회원가입 이메일 인증번호 확인",
        description="이메일로 발송된 6자리 인증번호를 확인합니다.",
        request=RegisterEmailVerifySerializer,
        responses={
            200: inline_serializer(
                name="RegisterEmailVerifyResponse",
                fields={
                    "detail": serializers.CharField(),
                    "verification_token": serializers.CharField(),
                },
            ),
            400: OpenApiResponse(description="인증번호 불일치/만료/시도 횟수 초과"),
        },
    )
    def post(self, request):
        serializer = RegisterEmailVerifySerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        try:
            verification_token = verify_signup_code(
                email,
                code,
            )

        except SignupCodeVerificationError as error:
            return Response(
                {
                    "detail": str(error),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "detail": "이메일 인증이 완료되었습니다.",
                "verification_token": verification_token,
            },
            status=status.HTTP_200_OK,
        )
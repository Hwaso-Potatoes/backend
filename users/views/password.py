from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from urllib.parse import urlencode

from ..serializers import PasswordChangeSerializer, PasswordResetConfirmSerializer, PasswordResetRequestSerializer
from ..utils import send_password_reset_email


User = get_user_model()


# 비밀번호 재설정(로그인시)
class PasswordResetView(APIView):
    """비밀번호 재설정 (새 비밀번호 두 번 입력)"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=PasswordChangeSerializer, responses={200: None})
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"detail": "비밀번호가 변경되었습니다."})


# 비밀번호 재설정 요청(비로그인시)
class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["인증"],
        summary="비밀번호 재설정 링크 발송",
        description=("비밀번호 재설정 링크를 발송합니다."),
        request=PasswordResetRequestSerializer,
        responses={
            200: inline_serializer(
                name="PasswordResetRequestResponse",
                fields={
                    "detail": serializers.CharField(),
                },
            ),
            503: OpenApiResponse(description="이메일 발송 실패"),
        },
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        user = User.objects.filter(
            email__iexact=email,
            is_active=True,
        ).first()

        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            token = default_token_generator.make_token(user)

            query = urlencode({
                "uid": uid,
                "token": token,
            })

            reset_link = (
                f"{settings.FRONTEND_BASE_URL.rstrip('/')}"
                f"/#/reset-password?{query}"
            )

            try:
                send_password_reset_email(
                    email,
                    reset_link,
                )
            except Exception:
                return Response(
                    {
                        "detail": (
                            "비밀번호 재설정 메일 발송에 실패했습니다."
                        ),
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        return Response(
            {
                "detail": ("비밀번호 재설정 링크를 발송했습니다."),
            },
            status=status.HTTP_200_OK,
        )


# 비밀번호 재설정(비로그인시)
class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["인증"],
        summary="비밀번호 재설정",
        description=("비밀번호 재설정 링크에서 전달된 uid와 token을 검증한 뒤 새 비밀번호를 설정합니다."),
        request=PasswordResetConfirmSerializer,
        responses={
            200: inline_serializer(
                name="PasswordResetConfirmResponse",
                fields={
                    "detail": serializers.CharField(),
                },
            ),
            400: OpenApiResponse(description="유효하지 않거나 만료된 재설정 링크"),
        },
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user_id = force_str(
                urlsafe_base64_decode(uid)
            )

            user = User.objects.get(
                pk=user_id,
                is_active=True,
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist,
        ):
            return Response(
                {
                    "detail": ("유효하지 않거나 만료된 비밀번호 재설정 링크입니다."),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {
                    "detail": ("유효하지 않거나 만료된 비밀번호 재설정 링크입니다."),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(
            update_fields=["password"]
        )

        return Response(
            {
                "detail": "비밀번호가 재설정되었습니다."
            },
            status=status.HTTP_200_OK,
        )
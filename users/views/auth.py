from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from ..serializers import LogoutSerializer, RegisterSerializer, SocialLoginSerializer
from ..social import PROVIDERS


User = get_user_model()


# 회원가입
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["인증"],
        summary="회원가입",
        description="새로운 사용자를 등록하고 JWT 토큰을 발급합니다.",
        request=RegisterSerializer,
        responses={
            201: inline_serializer(
                name="RegisterResponse",
                fields={
                    "id": serializers.IntegerField(),
                    "access": serializers.CharField(),
                    "refresh": serializers.CharField(),
                },
            ),
            400: OpenApiResponse(description="잘못된 요청"),
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "id": user.id,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


# 로그인
class LoginView(TokenObtainPairView):
    @extend_schema(
        tags=["인증"],
        summary="로그인",
        description="이메일과 비밀번호로 로그인하고 토큰을 발급받습니다.",
        request=inline_serializer(
            name="LoginRequest",
            fields={
                "email": serializers.EmailField(),
                "password": serializers.CharField(
                    write_only=True,
                    trim_whitespace=False,
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="LoginResponse",
                fields={
                    "refresh": serializers.CharField(),
                    "access": serializers.CharField(),
                },
            ),
            401: OpenApiResponse(description="인증 실패"),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# Access Token 재발급
class RefreshView(TokenRefreshView):
    @extend_schema(
        tags=["인증"],
        summary="Access Token 재발급",
        description="Refresh Token으로 Access Token을 재발급합니다.",
        request=inline_serializer(
            name="TokenRefreshRequest",
            fields={
                "refresh": serializers.CharField(
                    trim_whitespace=False,
                ),
            },
        ),
        responses={
            200: inline_serializer(
                name="TokenRefreshResponse",
                fields={
                    "access": serializers.CharField(),
                },
            ),
            401: OpenApiResponse(description="인증 실패"),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# 로그아웃
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["인증"],
        summary="로그아웃",
        description="Refresh Token을 폐기합니다.",
        request=LogoutSerializer,
        responses={
            204: OpenApiResponse(description="로그아웃 성공"),
            400: OpenApiResponse(description="잘못된 요청"),
            401: OpenApiResponse(description="인증 실패"),
        },
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


# 소셜 로그인(kakao/google/apple)
class SocialLoginView(APIView):
    """POST /api/users/social/<provider>/  (provider: kakao|google|apple)"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=SocialLoginSerializer,
        responses={200: None},
    )
    def post(self, request, provider):
        entry = PROVIDERS.get(provider)

        if not entry:
            return Response(
                {"detail": "지원하지 않는 소셜입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_field, get_user_info = entry

        token = request.data.get(token_field)

        if not token:
            return Response(
                {"detail": f"{token_field}가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            info = get_user_info(token)
        except Exception:
            return Response(
                {"detail": "소셜 인증에 실패했습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = info.get("email") or f"{provider}_{info['id']}@social.local"

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "nickname": info.get("nickname") or None,
            },
        )

        if created:
            user.set_unusable_password()
            user.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "is_new": created,
            }
        )
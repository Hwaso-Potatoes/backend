from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import LogoutSerializer, RegisterSerializer, DetailSerializer, UpdateSerializer
from drf_spectacular.utils import extend_schema
from .serializers import PasswordChangeSerializer
from .serializers import EmailChangeSerializer

import requests
from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .social import PROVIDERS
from drf_spectacular.utils import extend_schema
from .serializers import SocialLoginSerializer

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["인증"],
        summary="회원가입",
        description="새로운 사용자를 등록합니다.",
        request=RegisterSerializer,
        responses={
            201: inline_serializer(
                name="RegisterResponse",
                fields={
                    "id": serializers.IntegerField(),
                },
            ),
            400: OpenApiResponse(description="잘못된 요청"),
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            {
                "id": user.id,
            },
            status=status.HTTP_201_CREATED,
        )


class DetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["사용자"],
        summary="사용자 프로필 조회",
        description="사용자 프로필을 조회합니다.",
        responses={
            200: DetailSerializer,
            404: OpenApiResponse(description="사용자를 찾을 수 없음"),
        },
    )
    
    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)

        serializer = DetailSerializer(user)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["사용자"],
        summary="사용자 프로필 수정",
        description="사용자의 닉네임을 수정합니다.",
        request=UpdateSerializer,
        responses={
            200: inline_serializer(
                name="UserUpdateResponse",
                fields={
                    "id": serializers.IntegerField(),
                },
            ),
            400: OpenApiResponse(description="잘못된 요청"),
            401: OpenApiResponse(description="인증 실패"),
            403: OpenApiResponse(description="수정 권한 없음"),
            404: OpenApiResponse(description="사용자를 찾을 수 없음"),
        },
    )
    def patch(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)

        if request.user.pk != user.pk:
            return Response(
                {
                    "detail": "본인의 프로필만 수정할 수 있습니다.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = UpdateSerializer(
            user,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        updated_user = serializer.save()

        return Response(
            {
                "id": updated_user.id,
            },
            status=status.HTTP_200_OK,
        )


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
    
class EmailChangeView(APIView):
    """이메일 변경 (로그인 상태)"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=EmailChangeSerializer, responses={200: None})
    def post(self, request):
        serializer = EmailChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_email = serializer.validated_data["email"]
        user = request.user

    
        if User.objects.exclude(pk=user.pk).filter(email=new_email).exists():
            return Response({"email": "이미 사용 중인 이메일입니다."},
                            status=status.HTTP_400_BAD_REQUEST)

        user.email = new_email
        user.save()
        return Response({"detail": "이메일이 변경되었습니다.", "email": new_email})

class SocialLoginView(APIView):
    """POST /api/users/social/<provider>/  (provider: kakao|google|apple)"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=SocialLoginSerializer, responses={200: None})   # ← 추가
    def post(self, request, provider):
        entry = PROVIDERS.get(provider)
        if not entry:
            return Response({"detail": "지원하지 않는 소셜입니다."}, status=status.HTTP_400_BAD_REQUEST)
        token_field, get_user_info = entry

        token = request.data.get(token_field)
        if not token:
            return Response({"detail": f"{token_field}가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            info = get_user_info(token)
        except Exception:
            return Response({"detail": "소셜 인증에 실패했습니다."}, status=status.HTTP_400_BAD_REQUEST)

        email = info.get("email") or f"{provider}_{info['id']}@social.local"
        user, created = User.objects.get_or_create(
            email=email, defaults={"nickname": info.get("nickname", "")},
        )
        if created:
            user.set_unusable_password()
            user.save()

        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token),
                         "refresh": str(refresh),
                         "is_new": created})
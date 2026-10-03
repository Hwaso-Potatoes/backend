from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from ..models import SocialAccount
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


# 소셜 토큰 검증 (소셜 로그인 / SNS 계정 연동 공통)
def fetch_social_info(provider, data):
    """(info, None) 또는 (None, 에러 응답)"""
    entry = PROVIDERS.get(provider)

    if not entry:
        return None, Response(
            {"detail": "지원하지 않는 소셜입니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    token_field, get_user_info = entry

    token = data.get(token_field)

    if not token:
        return None, Response(
            {"detail": f"{token_field}가 필요합니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        return get_user_info(token), None
    except Exception:
        return None, Response(
            {"detail": "소셜 인증에 실패했습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )


SocialAccountsResponse = inline_serializer(
    name="SocialAccountsResponse",
    fields={
        "social_accounts": serializers.DictField(child=serializers.BooleanField()),
    },
)


# 소셜 로그인(kakao/google/apple)
class SocialLoginView(APIView):
    """POST /api/users/social/<provider>/  (provider: kakao|google|apple)"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["인증"],
        summary="소셜 로그인",
        description=(
            "kakao/google은 access_token, apple은 identity_token으로 로그인하고 JWT 토큰을 발급합니다. "
            "연동된 소셜 계정이 없으면 같은 이메일의 계정에 연동하거나 새로 가입합니다."
        ),
        request=SocialLoginSerializer,
        responses={
            200: inline_serializer(
                name="SocialLoginResponse",
                fields={
                    "access": serializers.CharField(),
                    "refresh": serializers.CharField(),
                    "is_new": serializers.BooleanField(),
                },
            ),
            400: OpenApiResponse(description="지원하지 않는 소셜 / 소셜 인증 실패"),
        },
    )
    def post(self, request, provider):
        info, error_response = fetch_social_info(provider, request.data)

        if error_response:
            return error_response

        account = (
            SocialAccount.objects
            .select_related("user")
            .filter(provider=provider, uid=info["id"])
            .first()
        )

        created = False

        if account is not None:
            user = account.user
        else:
            email = (info.get("email") or f"{provider}_{info['id']}@social.local").lower()

            # nickname 컬럼이 max_length=8이라 소셜 이름이 길면 잘라서 저장
            nickname = (info.get("nickname") or "")[:8] or None

            with transaction.atomic():
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "nickname": nickname,
                    },
                )

                if created:
                    user.set_unusable_password()
                    user.save()

                # 처음 로그인한 소셜 계정 → 연동 등록 (같은 이메일의 기존 계정 포함)
                if not SocialAccount.objects.filter(user=user, provider=provider).exists():
                    SocialAccount.objects.create(
                        user=user,
                        provider=provider,
                        uid=info["id"],
                        email=info.get("email") or "",
                    )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "is_new": created,
            }
        )


# SNS 계정 연동/해제 (환경설정)
class SocialLinkView(APIView):
    """POST·DELETE /api/users/social/<provider>/link/"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["사용자"],
        summary="SNS 계정 연동",
        description="로그인한 계정에 소셜 계정을 연동합니다. 요청 바디는 소셜 로그인과 같습니다.",
        request=SocialLoginSerializer,
        responses={
            200: OpenApiResponse(response=SocialAccountsResponse, description="이미 연동된 계정"),
            201: OpenApiResponse(response=SocialAccountsResponse, description="연동 완료"),
            400: OpenApiResponse(description="지원하지 않는 소셜 / 소셜 인증 실패"),
            401: OpenApiResponse(description="인증 실패"),
            409: OpenApiResponse(description="다른 계정에 연동된 소셜 계정 / 같은 소셜의 다른 계정이 이미 연동됨"),
        },
    )
    def post(self, request, provider):
        info, error_response = fetch_social_info(provider, request.data)

        if error_response:
            return error_response

        user = request.user

        account = SocialAccount.objects.filter(provider=provider, uid=info["id"]).first()

        if account is not None and account.user_id != user.pk:
            return Response(
                {"detail": "이미 다른 계정에 연동된 소셜 계정입니다."},
                status=status.HTTP_409_CONFLICT,
            )

        if account is not None:
            return Response(
                {"social_accounts": SocialAccount.linked_status(user)},
                status=status.HTTP_200_OK,
            )

        if SocialAccount.objects.filter(user=user, provider=provider).exists():
            return Response(
                {"detail": "같은 소셜의 다른 계정이 이미 연동되어 있습니다. 연동 해제 후 다시 시도해 주세요."},
                status=status.HTTP_409_CONFLICT,
            )

        SocialAccount.objects.create(
            user=user,
            provider=provider,
            uid=info["id"],
            email=info.get("email") or "",
        )

        return Response(
            {"social_accounts": SocialAccount.linked_status(user)},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["사용자"],
        summary="SNS 계정 연동 해제",
        description="연동된 소셜 계정을 해제합니다. 비밀번호 없이 소셜로만 가입한 계정은 마지막 연동을 해제할 수 없습니다.",
        request=None,
        responses={
            200: SocialAccountsResponse,
            400: OpenApiResponse(description="지원하지 않는 소셜 / 다른 로그인 수단 없음"),
            401: OpenApiResponse(description="인증 실패"),
            404: OpenApiResponse(description="연동된 계정 없음"),
        },
    )
    def delete(self, request, provider):
        if provider not in SocialAccount.Provider.values:
            return Response(
                {"detail": "지원하지 않는 소셜입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user

        account = SocialAccount.objects.filter(user=user, provider=provider).first()

        if account is None:
            return Response(
                {"detail": "연동된 계정이 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 소셜로만 가입한 계정이 마지막 연동까지 해제하면 로그인할 방법이 없어짐
        if (
            not user.has_usable_password()
            and not SocialAccount.objects.filter(user=user).exclude(pk=account.pk).exists()
        ):
            return Response(
                {"detail": "다른 로그인 수단이 없어 연동을 해제할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account.delete()

        return Response(
            {"social_accounts": SocialAccount.linked_status(user)},
            status=status.HTTP_200_OK,
        )

from django.contrib.auth import get_user_model
from django.contrib.postgres.search import TrigramSimilarity
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics, permissions


from .models import Friend
from walk.models import WalkingSession
from .serializers import (
    FriendListSerializer,
    FriendQRCreateResultSerializer,
    FriendQRRedeemResultSerializer,
    FriendQRRedeemSerializer,
)
from .services import (
    FRIEND_QR_TTL_SECONDS,
    FriendQRTokenError,
    consume_friend_qr_token,
    generate_friend_qr_token,
    get_friend_qr_owner_id,
)


User = get_user_model()


class FriendListView(generics.ListAPIView):
    serializer_class = FriendListSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["친구"],
        summary="친구 목록 조회",
        description="현재 사용자의 친구 목록을 조회하며 닉네임으로 부분 및 유사 검색할 수 있습니다.",
        parameters=[
            OpenApiParameter(
                name="nickname",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="검색할 친구 닉네임",
            ),
        ],
        responses={
            200: FriendListSerializer(many=True),
            401: OpenApiResponse(description="인증 실패"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        active_walks = WalkingSession.objects.filter(
            user_id=OuterRef("pk"),
            status__in=["WALKING", "PAUSED"],
        )

        queryset = (
            User.objects
            .filter(
                Q(
                    friendships_as_user1__user2=self.request.user,
                )
                | Q(
                    friendships_as_user2__user1=self.request.user,
                ),
                is_active=True,
            )
            .annotate(
                is_walking=Exists(active_walks),
            )
            .prefetch_related("pets")
            .distinct()
        )

        nickname = self.request.query_params.get(
            "nickname",
            "",
        ).strip()

        if not nickname:
            return queryset.order_by("nickname")

        return (
            queryset
            .annotate(
                similarity=TrigramSimilarity(
                    "nickname",
                    nickname,
                )
            )
            .filter(
                Q(nickname__icontains=nickname)
                | Q(similarity__gte=0.2)
            )
            .order_by(
                "-similarity",
                "nickname",
            )
        )


class FriendQRCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["친구"],
        summary="친구 추가 QR 생성",
        description="현재 사용자의 친구 추가용 QR 토큰을 생성합니다.",
        request=None,
        responses={
            200: FriendQRCreateResultSerializer,
            401: OpenApiResponse(description="인증 실패"),
        },
    )
    def post(self, request):
        token = generate_friend_qr_token(
            request.user.id,
        )

        return Response(
            {
                "token": token,
                "expires_in": FRIEND_QR_TTL_SECONDS,
            },
            status=status.HTTP_200_OK,
        )


class FriendQRRedeemView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["친구"],
        summary="QR 스캔 친구 추가",
        description="스캔한 QR 토큰을 검증하고 해당 사용자와 친구 관계를 생성합니다.",
        request=FriendQRRedeemSerializer,
        responses={
            201: FriendQRRedeemResultSerializer,
            400: OpenApiResponse(description="잘못된 요청"),
            401: OpenApiResponse(description="인증 실패"),
            404: OpenApiResponse(description="사용자를 찾을 수 없음"),
        },
    )
    def post(self, request):
        serializer = FriendQRRedeemSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]

        try:
            target_user_id = get_friend_qr_owner_id(token)
        except FriendQRTokenError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if target_user_id == request.user.id:
            return Response(
                {
                    "detail": "자기 자신은 친구로 추가할 수 없습니다.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_user = get_object_or_404(
            User,
            id=target_user_id,
            is_active=True,
        )

        user1_id, user2_id = sorted([
            request.user.id,
            target_user.id,
        ])

        if Friend.objects.filter(
            user1_id=user1_id,
            user2_id=user2_id,
        ).exists():
            return Response(
                {
                    "detail": "이미 친구로 등록된 사용자입니다.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            consume_friend_qr_token(token)
        except FriendQRTokenError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                friendship = Friend.objects.create(
                    user1_id=user1_id,
                    user2_id=user2_id,
                )
        except IntegrityError:
            return Response(
                {
                    "detail": "이미 친구로 등록된 사용자입니다.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "id": friendship.id,
                "friend": FriendListSerializer(
                    target_user,
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class FriendDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["친구"],
        summary="친구 삭제",
        description="현재 사용자와 해당 사용자의 친구 관계를 삭제합니다.",
        responses={
            204: OpenApiResponse(description="친구 삭제 성공"),
            401: OpenApiResponse(description="인증 실패"),
            404: OpenApiResponse(description="친구 관계를 찾을 수 없음"),
        },
    )
    def delete(self, request, friend_id):
        user1_id, user2_id = sorted([
            request.user.id,
            friend_id,
        ])

        friendship = get_object_or_404(
            Friend,
            user1_id=user1_id,
            user2_id=user2_id,
        )

        friendship.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
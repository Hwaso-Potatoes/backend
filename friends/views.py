from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Friend
from .serializers import CreateResultSerializer, CreateSerializer, ListSerializer, ReceivedSerializer, RespondSerializer


class FriendView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["친구"],
        summary="친구 목록 조회",
        description="현재 사용자의 친구 목록을 조회합니다.",
        responses={
            200: ListSerializer(many=True),
            401: OpenApiResponse(description="인증 실패"),
        },
    )
    def get(self, request):
        relationships = Friend.objects.filter(
            Q(requester=request.user)
            | Q(receiver=request.user),
            status=Friend.Status.ACCEPTED,
        ).select_related(
            "requester",
            "receiver",
        )

        friends = [
            relationship.receiver
            if relationship.requester_id == request.user.id
            else relationship.requester
            for relationship in relationships
        ]

        serializer = ListSerializer(
            friends,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["친구"],
        summary="친구 요청 보내기",
        description="다른 사용자에게 친구 요청을 보냅니다.",
        request=CreateSerializer,
        responses={
            201: CreateResultSerializer,
            400: OpenApiResponse(description="잘못된 요청"),
            401: OpenApiResponse(description="인증 실패"),
        },
    )
    def post(self, request):
        serializer = CreateSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )
        serializer.is_valid(raise_exception=True)

        friend_request = serializer.save()

        response_serializer = CreateResultSerializer(
            friend_request,
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class ReceivedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["친구"],
        summary="받은 친구 요청 조회",
        description="현재 사용자가 받은 친구 요청을 조회합니다.",
        responses={
            200: ReceivedSerializer(many=True),
            401: OpenApiResponse(description="인증 실패"),
        },
    )
    def get(self, request):
        friend_requests = Friend.objects.filter(
            receiver=request.user,
            status=Friend.Status.PENDING,
        ).select_related("requester")

        serializer = ReceivedSerializer(
            friend_requests,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class RespondView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["친구"],
        summary="친구 요청 수락/거절",
        description="받은 친구 요청을 수락하거나 거절합니다.",
        request=RespondSerializer,
        responses={
            204: OpenApiResponse(description="친구 요청 처리 성공"),
            400: OpenApiResponse(description="잘못된 요청"),
            401: OpenApiResponse(description="인증 실패"),
            403: OpenApiResponse(description="처리 권한 없음"),
            404: OpenApiResponse(description="친구 요청을 찾을 수 없음"),
        },
    )
    def patch(self, request, request_id):
        friend_request = get_object_or_404(
            Friend,
            pk=request_id,
        )

        if friend_request.receiver != request.user:
            return Response(
                {
                    "detail": "받은 친구 요청만 처리할 수 있습니다.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if friend_request.status != Friend.Status.PENDING:
            return Response(
                {
                    "detail": "이미 처리된 친구 요청입니다.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RespondSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]

        if action == "accept":
            friend_request.status = Friend.Status.ACCEPTED
            friend_request.save(
                update_fields=(
                    "status",
                    "updated_at",
                )
            )

            return Response(
                status=status.HTTP_204_NO_CONTENT,
            )

        friend_request.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


class DeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["친구"],
        summary="친구 삭제",
        description="현재 사용자와 해당 사용자의 친구 관계를 삭제합니다.",
        responses={
            204: OpenApiResponse(
                description="친구 삭제 성공",
            ),
            401: OpenApiResponse(
                description="인증 실패",
            ),
            404: OpenApiResponse(
                description="친구 관계를 찾을 수 없음",
            ),
        },
    )
    def delete(self, request, friend_id):
        friendship = get_object_or_404(
            Friend.objects.filter(
                status=Friend.Status.ACCEPTED,
            ).filter(
                Q(
                    requester=request.user,
                    receiver_id=friend_id,
                )
                | Q(
                    requester_id=friend_id,
                    receiver=request.user,
                )
            )
        )

        friendship.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
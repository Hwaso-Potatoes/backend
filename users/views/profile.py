from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers import DetailSerializer, UpdateSerializer


User = get_user_model()


# 사용자 프로필 조회 및 수정
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
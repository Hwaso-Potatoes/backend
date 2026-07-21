from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from missions.models import PetBadge
from missions.serializers.badge import BadgeListSerializer
from pets.models import Pet


class BadgeListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["배지"],
        summary="반려견 배지 목록 조회",
        description="해당 반려견이 획득한 배지 목록을 조회합니다.",
        responses={
            200: BadgeListSerializer(many=True),
            401: OpenApiResponse(description="인증 실패"),
            404: OpenApiResponse(description="반려견을 찾을 수 없음"),
        },
    )
    def get(self, request, pet_id):
        pet = get_object_or_404(
            Pet,
            pk=pet_id,
            user=request.user,
        )

        pet_badges = (
            PetBadge.objects
            .filter(pet=pet)
            .select_related("badge")
            .order_by("-acquired_at")
        )

        serializer = BadgeListSerializer(
            pet_badges,
            many=True,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
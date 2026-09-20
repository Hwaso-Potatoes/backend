from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from missions.models import Badge
from missions.serializers.badge import BadgeSerializer, PetBadgeListSerializer
from pets.models import Pet


class BadgeListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["배지"],
        summary="전체 배지 조회",
        description="서비스에 존재하는 전체 배지 목록을 조회합니다.",
        responses={
            200: BadgeSerializer(many=True),
            401: OpenApiResponse(description="인증 실패"),
        },
    )
    def get(self, request):
        badges = Badge.objects.all().order_by("id")

        serializer = BadgeSerializer(
            badges,
            many=True,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
    

class PetBadgeListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["배지"],
        summary="반려견 보유 배지 조회",
        description="해당 반려견이 획득한 배지 목록을 조회합니다.",
        responses={
            200: PetBadgeListSerializer(many=True),
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
            pet.pet_badges
            .select_related("badge")
            .order_by("-acquired_at")
        )

        serializer = PetBadgeListSerializer(
            pet_badges,
            many=True,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
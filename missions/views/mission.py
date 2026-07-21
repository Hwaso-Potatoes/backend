from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from missions.models import PetMission
from missions.serializers.mission import MissionListQuerySerializer, MissionListSerializer
from pets.models import Pet


class MissionListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["미션"],
        summary="반려견 미션 목록 조회",
        description=(
            "해당 반려견의 현재 일일 또는 주간 미션과 "
            "진행 상태를 조회합니다."
        ),
        parameters=[
            OpenApiParameter(
                name="period",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                enum=[
                    "DAILY",
                    "WEEKLY",
                ],
                description="조회할 미션 기간",
            ),
        ],
        responses={
            200: MissionListSerializer(many=True),
            400: OpenApiResponse(description="잘못된 기간 값"),
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

        query_serializer = MissionListQuerySerializer(
            data=request.query_params,
        )
        query_serializer.is_valid(raise_exception=True)

        period = query_serializer.validated_data["period"]
        today = timezone.localdate()

        pet_missions = (
            PetMission.objects
            .filter(
                pet=pet,
                mission__period=period,
                period_start__lte=today,
                period_end__gte=today,
            )
            .select_related(
                "mission",
                "mission__reward_badge",
                "mission__reward_accessory",
            )
            .order_by("mission_id")
        )

        serializer = MissionListSerializer(
            pet_missions,
            many=True,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
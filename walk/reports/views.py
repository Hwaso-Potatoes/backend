from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from pets.models import Pet
from walk.reports.serializers import (
    PetWalkReportSerializer,
    ReportPeriod,
    ReportQuerySerializer,
)
from walk.reports.services import build_walk_report


class PetWalkReportView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    @extend_schema(
        tags=["산책 리포트"],
        summary="반려견 산책 리포트 조회",
        description=("선택한 기간과 날짜를 기준으로 산책 거리 비교, 추이 그래프, 주요 산책 구간 통계를 조회합니다."),
        parameters=[
            OpenApiParameter(
                name="period",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[
                    ReportPeriod.DAY,
                    ReportPeriod.MONTH,
                    ReportPeriod.YEAR,
                ],
                description=(
                    "리포트 조회 기간입니다. "
                    "DAY, MONTH, YEAR 중 선택하며 "
                    "생략하면 DAY가 사용됩니다."
                ),
            ),
            OpenApiParameter(
                name="date",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description=("조회 기준 날짜: YYYY-MM-DD 형식이며 생략하면 오늘 날짜가 사용됩니다."),
            ),
        ],
        responses={
            200: PetWalkReportSerializer,
            400: OpenApiResponse(description="잘못된 조회 조건"),
            401: OpenApiResponse(description="인증 실패"),
            404: OpenApiResponse(description="반려견을 찾을 수 없음"),
        },
    )
    def get(self, request, pet_id):
        query_serializer = ReportQuerySerializer(
            data=request.query_params,
        )
        query_serializer.is_valid(
            raise_exception=True,
        )

        period = (
            query_serializer
            .validated_data["period"]
        )
        anchor_date = (
            query_serializer
            .validated_data["date"]
        )

        pet = get_object_or_404(
            Pet,
            id=pet_id,
            user=request.user,
        )

        report_data = build_walk_report(
            pet=pet,
            period=period,
            anchor_date=anchor_date,
        )

        response_serializer = (
            PetWalkReportSerializer(
                instance=report_data,
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )
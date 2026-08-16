from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from pets.models import Pet
from walk.reports.serializers import PetWalkReportSerializer, ReportPeriodQuerySerializer
from walk.reports.services import get_completed_walks, get_report_chart, get_report_date_range, get_report_summary, get_growth_report, get_earned_badges


class PetWalkReportView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    @extend_schema(
        tags=["산책 리포트"],
        summary="반려견 산책 리포트 조회",
        description=(
            "선택한 기간의 산책 기록을 집계하여 "
            "요약 통계와 그래프 데이터를 반환합니다."
        ),
        parameters=[
            OpenApiParameter(
                name="period",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=[
                    "DAY",
                    "WEEK",
                    "MONTH",
                    "SIX_MONTHS",
                    "YEAR",
                ],
                description=(
                    "조회 기간입니다. "
                    "생략하면 WEEK가 사용됩니다."
                ),
            ),
        ],
        responses={
            200: PetWalkReportSerializer,
            400: OpenApiResponse(description="잘못된 기간 값"),
            401: OpenApiResponse(description="인증 실패"),
            404: OpenApiResponse(description="반려견을 찾을 수 없음"),
        },
    )
    def get(self, request, pet_id):
        query_serializer = ReportPeriodQuerySerializer(
            data=request.query_params
        )
        query_serializer.is_valid(
            raise_exception=True
        )

        period = query_serializer.validated_data[
            "period"
        ]

        pet = get_object_or_404(
            Pet,
            id=pet_id,
            user=request.user,
        )

        start_date, end_date = get_report_date_range(
            period
        )

        walks = get_completed_walks(
            pet=pet,
            start_date=start_date,
            end_date=end_date,
        )

        response_data = {
            "pet_id": pet.id,
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "summary": get_report_summary(walks),
            "chart": get_report_chart(
                walks=walks,
                period=period,
                start_date=start_date,
                end_date=end_date,
            ),
            "growth": get_growth_report(
                pet=pet,
                start_date=start_date,
                end_date=end_date,
            ),
            "earned_badges": get_earned_badges(
                pet=pet,
                start_date=start_date,
                end_date=end_date,
            ),
        }

        response_serializer = PetWalkReportSerializer(
            instance=response_data
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )
import calendar
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Attendance,
    AttendanceReward,
    AttendanceRewardDay,
)
from .serializers import (
    AttendanceCalendarQuerySerializer,
    AttendanceRewardSerializer,
)
from .services import get_attendance_streaks


class AttendanceSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()

        current_streak, best_streak = (
            get_attendance_streaks(
                request.user
            )
        )

        week_start = (
            today
            - timedelta(
                days=today.weekday()
            )
        )

        week_end = (
            week_start
            + timedelta(days=6)
        )

        attendances = list(
            Attendance.objects
            .filter(
                user=request.user,
                attendance_date__range=(
                    week_start,
                    week_end,
                ),
            )
        )

        attendance_by_date = {
            attendance.attendance_date:
                attendance
            for attendance in attendances
        }

        reward_days = set(
            AttendanceRewardDay.objects
            .filter(
                reward_date__range=(
                    week_start,
                    week_end,
                ),
            )
            .values_list(
                "reward_date",
                flat=True,
            )
        )

        rewards = (
            AttendanceReward.objects
            .filter(
                attendance__in=attendances,
            )
            .select_related(
                "attendance",
                "accessory",
            )
        )

        reward_by_attendance_id = {
            reward.attendance_id:
                reward
            for reward in rewards
        }

        week = []

        for index in range(7):
            day = (
                week_start
                + timedelta(days=index)
            )

            attendance = (
                attendance_by_date.get(
                    day
                )
            )

            reward = None

            if attendance:
                reward = (
                    reward_by_attendance_id
                    .get(attendance.id)
                )

            week.append({
                "date": day,
                "attended":
                    attendance is not None,
                "is_reward_day":
                    day in reward_days,
                "reward_received":
                    reward is not None,
            })

        today_attendance = (
            attendance_by_date.get(today)
        )

        today_reward = None

        if today_attendance:
            today_reward = (
                reward_by_attendance_id
                .get(
                    today_attendance.id
                )
            )

        reward_data = None

        if today_reward:
            reward_data = (
                AttendanceRewardSerializer(
                    today_reward,
                    context={
                        "request": request,
                    },
                ).data
            )

        return Response(
            {
                "current_streak":
                    current_streak,
                "best_streak":
                    best_streak,
                "today": {
                    "date": today,
                    "attended":
                        today_attendance
                        is not None,
                    "is_reward_day":
                        today in reward_days,
                    "reward":
                        reward_data,
                },
                "week": week,
            },
            status=status.HTTP_200_OK,
        )


class AttendanceCalendarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query_serializer = (
            AttendanceCalendarQuerySerializer(
                data=request.query_params
            )
        )

        query_serializer.is_valid(
            raise_exception=True
        )

        year = (
            query_serializer
            .validated_data["year"]
        )

        month = (
            query_serializer
            .validated_data["month"]
        )

        last_day_number = (
            calendar.monthrange(
                year,
                month,
            )[1]
        )

        start_date = date(
            year,
            month,
            1,
        )

        end_date = date(
            year,
            month,
            last_day_number,
        )

        attendances = list(
            Attendance.objects
            .filter(
                user=request.user,
                attendance_date__range=(
                    start_date,
                    end_date,
                ),
            )
        )

        attendance_by_date = {
            attendance.attendance_date:
                attendance
            for attendance in attendances
        }

        reward_dates = set(
            AttendanceRewardDay.objects
            .filter(
                reward_date__range=(
                    start_date,
                    end_date,
                ),
            )
            .values_list(
                "reward_date",
                flat=True,
            )
        )

        rewarded_attendance_ids = set(
            AttendanceReward.objects
            .filter(
                attendance__in=attendances,
            )
            .values_list(
                "attendance_id",
                flat=True,
            )
        )

        days = []

        for day_number in range(
            1,
            last_day_number + 1,
        ):
            day = date(
                year,
                month,
                day_number,
            )

            attendance = (
                attendance_by_date.get(
                    day
                )
            )

            days.append({
                "date": day,
                "attended":
                    attendance is not None,
                "is_reward_day":
                    day in reward_dates,
                "reward_received":
                    (
                        attendance is not None
                        and
                        attendance.id
                        in rewarded_attendance_ids
                    ),
            })

        return Response(
            {
                "year": year,
                "month": month,
                "days": days,
            },
            status=status.HTTP_200_OK,
        )


class AttendanceRewardListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rewards = (
            AttendanceReward.objects
            .filter(
                attendance__user=
                    request.user,
            )
            .select_related(
                "attendance",
                "accessory",
            )
            .order_by(
                "-attendance__attendance_date",
                "-id",
            )
        )

        serializer = (
            AttendanceRewardSerializer(
                rewards,
                many=True,
                context={
                    "request": request,
                },
            )
        )

        return Response(
            {
                "rewards":
                    serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class AttendanceRewardOpenView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, reward_id):
        try:
            reward = (
                AttendanceReward.objects
                .select_for_update()
                .select_related(
                    "attendance",
                    "accessory",
                )
                .get(
                    id=reward_id,
                    attendance__user=
                        request.user,
                )
            )

        except AttendanceReward.DoesNotExist:
            return Response(
                {
                    "error": "존재하지 않는 출석 보상입니다."
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )

        if not reward.opened:
            reward.opened = True
            reward.opened_at = (
                timezone.now()
            )

            reward.save(
                update_fields=[
                    "opened",
                    "opened_at",
                ]
            )

        serializer = (
            AttendanceRewardSerializer(
                reward,
                context={
                    "request": request,
                },
            )
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
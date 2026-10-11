from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.services import send_push_notification


User = get_user_model()


class Command(BaseCommand):
    help = "주간/월간 산책 리포트 푸시 알림 전송"

    def handle(self, *args, **options):
        today = timezone.localdate()

        users = (
            User.objects
            .filter(
                is_active=True,
                device_tokens__is_active=True,
            )
            .distinct()
        )

        # 매주 월요일
        if today.weekday() == 0:
            self.send_weekly_report(
                users
            )

        # 매월 1일
        if today.day == 1:
            self.send_monthly_report(
                users,
                today,
            )

    def send_weekly_report(self, users):
        success_count = 0

        for user in users:
            success_count += (
                send_push_notification(
                    user=user,
                    notification_type="walk_report",
                    title=(
                        "지난주 산책 리포트가 "
                        "도착했어요!"
                    ),
                    body=(
                        "지난주 반려견과 함께한 "
                        "산책 기록을 확인해보세요."
                    ),
                    data={
                        "type": "walk_report",
                        "period": "weekly",
                    },
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"주간 리포트 알림 전송 완료: "
                f"{success_count}개"
            )
        )

    def send_monthly_report(self, users, today):
        last_month_date = (
            today.replace(day=1)
            - timedelta(days=1)
        )

        month = last_month_date.month

        success_count = 0

        for user in users:
            success_count += (
                send_push_notification(
                    user=user,
                    notification_type="walk_report",
                    title=(
                        f"{month}월 산책 리포트가 "
                        "도착했어요!"
                    ),
                    body=(
                        "지난달 반려견과 함께한 "
                        "산책 기록을 확인해보세요."
                    ),
                    data={
                        "type": "walk_report",
                        "period": "monthly",
                        "year": last_month_date.year,
                        "month": month,
                    },
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"월간 리포트 알림 전송 완료: "
                f"{success_count}개"
            )
        )
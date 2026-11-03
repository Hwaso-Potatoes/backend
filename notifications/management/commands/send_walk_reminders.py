from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import NotificationPreference
from notifications.services import send_push_notification
from walk.models import WalkingSession


class Command(BaseCommand):
    help = "설정된 시간에 산책 리마인더 푸시 알림 전송"

    def handle(self, *args, **options):
        now = timezone.localtime()
        today = now.date()

        preferences = (
            NotificationPreference.objects
            .select_related("user")
            .filter(
                user__is_active=True,
                allow_all=True,
                walk_reminder=True,
                walk_reminder_time__hour=now.hour,
                walk_reminder_time__minute=now.minute,
            )
            .exclude(
                last_walk_reminder_sent_date=today,
            )
        )

        success_count = 0

        for preference in preferences:
            user = preference.user

            # 오늘 이미 산책을 완료했다면 리마인더 생략
            already_walked_today = (
                WalkingSession.objects
                .filter(
                    user=user,
                    status="FINISHED",
                    end_time__date=today,
                )
                .exists()
            )

            if already_walked_today:
                continue

            sent_count = send_push_notification(
                user=user,
                notification_type="walk_reminder",
                title="산책할 시간이에요!",
                body="오늘도 반려견과 함께 산책해볼까요?",
                data={
                    "type": "walk_reminder",
                },
            )

            if sent_count > 0:
                preference.last_walk_reminder_sent_date = today
                preference.save(
                    update_fields=[
                        "last_walk_reminder_sent_date",
                    ]
                )

                success_count += sent_count

        self.stdout.write(
            self.style.SUCCESS(
                f"산책 리마인더 전송 완료: {success_count}개"
            )
        )
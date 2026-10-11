from django.contrib.auth import get_user_model
import logging

from firebase_admin import messaging

from .firebase import get_firebase_app
from .models import (
    DeviceToken,
    NotificationPreference,
)


logger = logging.getLogger(__name__)


User = get_user_model()


NOTIFICATION_PREFERENCE_FIELDS = {
    "walk_reminder": "walk_reminder",
    "walk_report": "walk_report",
    "level_badge": "level_badge",
    "accessory": "accessory",
    "friend_walk": "friend_walk",
    "marketing": "marketing",
}


def send_push_notification(*, user, notification_type, title, body, data=None):
    preference, _ = (
        NotificationPreference.objects
        .get_or_create(
            user=user,
        )
    )

    # 전체 알림 OFF
    if not preference.allow_all:
        return 0

    preference_field = (
        NOTIFICATION_PREFERENCE_FIELDS.get(
            notification_type
        )
    )

    # 해당 종류 알림 OFF
    if (
        preference_field
        and not getattr(
            preference,
            preference_field,
        )
    ):
        return 0

    devices = DeviceToken.objects.filter(
        user=user,
        is_active=True,
    )

    if not devices.exists():
        return 0

    firebase_app = get_firebase_app()

    # 아직 Firebase 설정이 안 된 개발 환경
    if firebase_app is None:
        return 0

    message_data = {
        str(key): str(value)
        for key, value in (data or {}).items()
    }

    success_count = 0

    for device in devices:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=message_data,
            token=device.token,
        )

        try:
            messaging.send(
                message,
                app=firebase_app,
            )

            success_count += 1

        except messaging.UnregisteredError:
            device.is_active = False
            device.save(
                update_fields=[
                    "is_active",
                ]
            )

        except Exception:
            logger.exception(
                "푸시 알림 전송 실패 "
                "(user_id=%s, device_id=%s)",
                user.id,
                device.id,
            )

    return success_count


def send_marketing_campaign(campaign):
    users = (
        User.objects
        .filter(
            is_active=True,
            notification_preference__allow_all=True,
            notification_preference__marketing=True,
            device_tokens__is_active=True,
        )
        .distinct()
    )

    success_count = 0

    for user in users:
        success_count += send_push_notification(
            user=user,
            notification_type="marketing",
            title=campaign.title,
            body=campaign.body,
            data=campaign.data,
        )

    return success_count
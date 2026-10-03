import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from missions.models import Accessory, PetAccessory

from .models import (
    Attendance,
    AttendanceReward,
    AttendanceRewardDay,
)


@transaction.atomic
def grant_random_unowned_accessory(*, attendance):
    attendance = (
        Attendance.objects
        .select_for_update()
        .select_related("pet")
        .get(id=attendance.id)
    )

    existing_reward = (
        AttendanceReward.objects
        .filter(attendance=attendance)
        .select_related("accessory")
        .first()
    )

    if existing_reward:
        return existing_reward

    pet = attendance.pet

    owned_accessory_ids = (
        PetAccessory.objects
        .filter(pet=pet)
        .values_list(
            "accessory_id",
            flat=True,
        )
    )

    candidate_ids = list(
        Accessory.objects
        .exclude(id__in=owned_accessory_ids)
        .values_list(
            "id",
            flat=True,
        )
    )

    if not candidate_ids:
        return None

    accessory_id = secrets.choice(
        candidate_ids
    )

    accessory = Accessory.objects.get(
        id=accessory_id
    )

    pet_accessory, created = (
        PetAccessory.objects.get_or_create(
            pet=pet,
            accessory=accessory,
        )
    )

    if not created:
        return grant_random_unowned_accessory(
            attendance=attendance,
        )

    reward = AttendanceReward.objects.create(
        attendance=attendance,
        accessory=accessory,
    )

    return reward


@transaction.atomic
def process_walk_attendance(*, user, pet, walk_date):
    attendance, _ = (
        Attendance.objects.get_or_create(
            user=user,
            attendance_date=walk_date,
            defaults={
                "pet": pet,
            },
        )
    )

    is_reward_day = (
        AttendanceRewardDay.objects
        .filter(
            reward_date=walk_date,
        )
        .exists()
    )

    reward = None

    if is_reward_day:
        reward = grant_random_unowned_accessory(
            attendance=attendance,
        )

    return attendance, reward


def get_attendance_streaks(user):
    attendance_dates = list(
        Attendance.objects
        .filter(user=user)
        .order_by("attendance_date")
        .values_list(
            "attendance_date",
            flat=True,
        )
    )

    if not attendance_dates:
        return 0, 0

    best_streak = 1
    streak = 1

    for index in range(
        1,
        len(attendance_dates),
    ):
        previous_date = (
            attendance_dates[index - 1]
        )
        current_date = (
            attendance_dates[index]
        )

        if (
            current_date - previous_date
        ).days == 1:
            streak += 1
            best_streak = max(
                best_streak,
                streak,
            )
        else:
            streak = 1

    today = timezone.localdate()
    latest_date = attendance_dates[-1]

    if latest_date < today - timedelta(days=1):
        current_streak = 0

    else:
        current_streak = 1

        for index in range(
            len(attendance_dates) - 1,
            0,
            -1,
        ):
            current_date = (
                attendance_dates[index]
            )
            previous_date = (
                attendance_dates[index - 1]
            )

            if (
                current_date - previous_date
            ).days == 1:
                current_streak += 1
            else:
                break

    return (
        current_streak,
        best_streak,
    )
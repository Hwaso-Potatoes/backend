from django.db.models import Sum
from django.utils import timezone

from missions.models import Badge, PetBadge


# 일정 조건 만족시, 뱃지 지급
def grant_badge(pet, badge):
    pet_badge, created = PetBadge.objects.get_or_create(
        pet=pet,
        badge=badge,
    )

    return pet_badge, created


# '첫 산책' 만족 여부 확인
def check_first_walk_badge(pet):
    badge = Badge.objects.filter(
        condition_type=Badge.ConditionType.FIRST_WALK,
    ).first()

    if not badge:
        return None

    finished_walk_count = pet.walking_sessions.filter(status="FINISHED").count()

    if finished_walk_count == 1:
        pet_badge, created = grant_badge(
            pet=pet,
            badge=badge,
        )

        if created:
            return pet_badge

    return None


# '일정 거리' 만족 여부 확인
def check_total_distance_badges(pet):
    total_distance = (
        pet.walking_sessions
        .filter(status="FINISHED")
        .aggregate(total=Sum("total_distance"))["total"]
        or 0
    )

    badges = Badge.objects.filter(
        condition_type=Badge.ConditionType.TOTAL_DISTANCE,
        goal__lte=total_distance,
    )

    acquired_badges = []

    for badge in badges:
        pet_badge, created = grant_badge(
            pet=pet,
            badge=badge,
        )

        if created:
            acquired_badges.append(pet_badge)

    return acquired_badges


# '누적 시간' 만족 여부 확인
def check_total_duration_badges(pet):
    total_duration = (
        pet.walking_sessions
        .filter(status="FINISHED")
        .aggregate(total=Sum("total_duration"))["total"]
        or 0
    )

    badges = Badge.objects.filter(
        condition_type=Badge.ConditionType.TOTAL_DURATION,
        goal__lte=total_duration,
    )

    acquired_badges = []

    for badge in badges:
        pet_badge, created = grant_badge(
            pet=pet,
            badge=badge,
        )

        if created:
            acquired_badges.append(pet_badge)

    return acquired_badges


# '하루 3회 산책' 만족 여부 확인
def check_daily_walk_count_badges(pet):
    today = timezone.localdate()

    walk_count = pet.walking_sessions.filter(
        status="FINISHED",
        end_time__date=today,
    ).count()

    badges = Badge.objects.filter(
        condition_type=Badge.ConditionType.DAILY_WALK_COUNT,
        goal__lte=walk_count,
    )

    acquired_badges = []

    for badge in badges:
        pet_badge, created = grant_badge(
            pet=pet,
            badge=badge,
        )

        if created:
            acquired_badges.append(pet_badge)

    return acquired_badges


# '연속 출석' 만족 여부 확인
def check_consecutive_days_badges(pet):
    walk_dates = list(
        pet.walking_sessions
        .filter(
            status="FINISHED",
            end_time__isnull=False,
        )
        .dates(
            "end_time",
            "day",
            order="DESC",
        )
    )

    if not walk_dates:
        return []

    consecutive_days = 1

    for i in range(1, len(walk_dates)):
        previous_date = walk_dates[i - 1]
        current_date = walk_dates[i]

        if (previous_date - current_date).days == 1:
            consecutive_days += 1
        else:
            break

    badges = Badge.objects.filter(
        condition_type=Badge.ConditionType.CONSECUTIVE_DAYS,
        goal__lte=consecutive_days,
    )

    acquired_badges = []

    for badge in badges:
        pet_badge, created = grant_badge(
            pet=pet,
            badge=badge,
        )

        if created:
            acquired_badges.append(pet_badge)

    return acquired_badges


# '레벨 50' 만족 여부 확인
def check_level_badges(pet):
    badges = Badge.objects.filter(
        condition_type=Badge.ConditionType.LEVEL,
        goal__lte=pet.level,
    )

    acquired_badges = []

    for badge in badges:
        pet_badge, created = grant_badge(
            pet=pet,
            badge=badge,
        )

        if created:
            acquired_badges.append(pet_badge)

    return acquired_badges
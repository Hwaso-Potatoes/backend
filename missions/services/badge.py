from django.db.models import Sum
from django.utils import timezone

from missions.models import Badge, PetBadge


# 뱃지 지급
def grant_badge(*, pet, badge):
    pet_badge, created = (
        PetBadge.objects.get_or_create(
            pet=pet,
            badge=badge,
        )
    )

    return pet_badge, created


# 숫자 goal 기반 뱃지 공통 지급
def grant_goal_badges(*, pet, condition_type, current_value):
    badges = (
        Badge.objects
        .filter(
            condition_type=condition_type,
            goal__isnull=False,
            goal__lte=current_value,
        )
        .order_by("goal")
    )

    acquired_badges = []

    for badge in badges:
        pet_badge, created = grant_badge(
            pet=pet,
            badge=badge,
        )

        if created:
            acquired_badges.append(
                pet_badge
            )

    return acquired_badges


# 첫 산책 뱃지
def check_first_walk_badges(pet):
    finished_walk_count = (
        pet.walking_sessions
        .filter(
            status="FINISHED",
        )
        .count()
    )

    return grant_goal_badges(
        pet=pet,
        condition_type=(
            Badge.ConditionType.FIRST_WALK
        ),
        current_value=finished_walk_count,
    )


# 누적 산책 거리 뱃지
def check_total_distance_badges(pet):
    total_distance = (
        pet.walking_sessions
        .filter(
            status="FINISHED",
        )
        .aggregate(
            total=Sum("total_distance"),
        )["total"]
        or 0
    )

    return grant_goal_badges(
        pet=pet,
        condition_type=(
            Badge.ConditionType.TOTAL_DISTANCE
        ),
        current_value=total_distance,
    )


# 누적 산책 시간 뱃지
def check_total_duration_badges(pet):
    total_duration = (
        pet.walking_sessions
        .filter(
            status="FINISHED",
        )
        .aggregate(
            total=Sum("total_duration"),
        )["total"]
        or 0
    )

    return grant_goal_badges(
        pet=pet,
        condition_type=(
            Badge.ConditionType.TOTAL_DURATION
        ),
        current_value=total_duration,
    )


# 하루 산책 횟수 뱃지
def check_daily_walk_count_badges(*, pet, walk_date):
    walk_count = (
        pet.walking_sessions
        .filter(
            status="FINISHED",
            end_time__date=walk_date,
        )
        .count()
    )

    return grant_goal_badges(
        pet=pet,
        condition_type=(
            Badge.ConditionType.DAILY_WALK_COUNT
        ),
        current_value=walk_count,
    )


# 연속 산책 일수 계산
def get_consecutive_walk_days(pet):
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
        return 0

    consecutive_days = 1

    for i in range(1, len(walk_dates)):
        previous_date = walk_dates[i - 1]
        current_date = walk_dates[i]

        if (
            previous_date - current_date
        ).days == 1:
            consecutive_days += 1
        else:
            break

    return consecutive_days


# 연속 산책 뱃지
def check_consecutive_days_badges(pet):
    consecutive_days = (
        get_consecutive_walk_days(pet)
    )

    return grant_goal_badges(
        pet=pet,
        condition_type=(
            Badge.ConditionType.CONSECUTIVE_DAYS
        ),
        current_value=consecutive_days,
    )


# 레벨 뱃지
def check_level_badges(pet):
    return grant_goal_badges(
        pet=pet,
        condition_type=(
            Badge.ConditionType.LEVEL
        ),
        current_value=pet.level,
    )


# 비/눈 산책 뱃지: WalkingSession에 산책 당시 날씨 정보가 저장되면 구현
def check_weather_badges(*, pet, session):
    return []


# 새로운 지역/숲/도시 산책 뱃지: 산책 경로의 지역 및 환경 타입을 판단할 수 있게 되면 구현
def check_location_badges(*, pet, session):
    acquired_badges = []

    condition_types = []

    if session.is_forest_walk is True:
        condition_types.append(
            Badge.ConditionType.FOREST_WALK
        )

    if session.is_city_walk is True:
        condition_types.append(
            Badge.ConditionType.CITY_WALK
        )

    if session.is_new_area is True:
        condition_types.append(
            Badge.ConditionType.NEW_REGION
        )

    for condition_type in condition_types:
        badges = Badge.objects.filter(
            condition_type=condition_type
        )

        for badge in badges:
            pet_badge, created = grant_badge(
                pet=pet,
                badge=badge,
            )

            if created:
                acquired_badges.append(
                    pet_badge
                )

    return acquired_badges


# 산책 종료 시 확인할 뱃지
def check_walk_badges(*, pet, session):
    acquired_badges = []

    acquired_badges.extend(
        check_first_walk_badges(
            pet
        )
    )

    acquired_badges.extend(
        check_total_distance_badges(
            pet
        )
    )

    acquired_badges.extend(
        check_total_duration_badges(
            pet
        )
    )

    acquired_badges.extend(
        check_daily_walk_count_badges(
            pet=pet,
            walk_date=timezone.localdate(
                session.end_time
            ),
        )
    )

    acquired_badges.extend(
        check_consecutive_days_badges(
            pet
        )
    )

    # 지급 로직 미구현
    acquired_badges.extend(
        check_weather_badges(
            pet=pet,
            session=session,
        )
    )

    return acquired_badges


# 첫 친구/호감도 친구 뱃지
def check_friend_badges(*, pet):
    return []
from calendar import monthrange
from datetime import date, datetime, time, timedelta

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from walk.models import WalkingSession
from walk.reports.serializers import ReportPeriodQuerySerializer
from pets.models import PetHistory
from missions.models import PetBadge


def get_report_date_range(period):
    today = timezone.localdate()
    Period = ReportPeriodQuerySerializer.Period

    if period == Period.DAY:
        return today, today

    if period == Period.WEEK:
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)

        return start_date, end_date

    if period == Period.MONTH:
        start_date = today.replace(day=1)
        last_day = monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day)

        return start_date, end_date

    if period == Period.SIX_MONTHS:
        start_month_index = (
            today.year * 12
            + today.month
            - 1
            - 5
        )

        start_year = start_month_index // 12
        start_month = start_month_index % 12 + 1

        start_date = date(
            year=start_year,
            month=start_month,
            day=1,
        )

        last_day = monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day)

        return start_date, end_date

    if period == Period.YEAR:
        start_date = date(
            year=today.year,
            month=1,
            day=1,
        )
        end_date = date(
            year=today.year,
            month=12,
            day=31,
        )

        return start_date, end_date

    raise ValueError("지원하지 않는 리포트 기간입니다.")


def get_completed_walks(*, pet, start_date, end_date):
    current_timezone = timezone.get_current_timezone()

    start_datetime = timezone.make_aware(
        datetime.combine(start_date, time.min),
        timezone=current_timezone,
    )

    # 종료일 다음 날 0시 미만으로 조회해 경계를 명확하게 처리한다.
    end_exclusive_datetime = timezone.make_aware(
        datetime.combine(
            end_date + timedelta(days=1),
            time.min,
        ),
        timezone=current_timezone,
    )

    return (
        WalkingSession.objects
        .filter(
            pet=pet,
            status="FINISHED",
            end_time__gte=start_datetime,
            end_time__lt=end_exclusive_datetime,
        )
        .only(
            "id",
            "end_time",
            "total_distance",
            "total_duration",
        )
        .order_by("end_time")
    )


def get_report_summary(walks):
    result = walks.aggregate(
        total_walk_count=Count("id"),
        total_distance_km=Sum("total_distance"),
        total_duration_minutes=Sum("total_duration"),
        average_distance_km=Avg("total_distance"),
        average_duration_minutes=Avg("total_duration"),
    )

    return {
        "total_walk_count": result["total_walk_count"],
        "total_distance_km": round(
            float(result["total_distance_km"] or 0),
            2,
        ),
        "total_duration_minutes": int(
            result["total_duration_minutes"] or 0
        ),
        "average_distance_km": round(
            float(result["average_distance_km"] or 0),
            2,
        ),
        "average_duration_minutes": round(
            float(result["average_duration_minutes"] or 0),
            1,
        ),
    }


def create_empty_bucket(label):
    return {
        "label": label,
        "distance_km": 0.0,
        "duration_minutes": 0,
        "walk_count": 0,
    }


def add_walk_to_bucket(bucket, walk):
    bucket["distance_km"] += float(
        walk.total_distance or 0
    )
    bucket["duration_minutes"] += int(
        walk.total_duration or 0
    )
    bucket["walk_count"] += 1


def get_months_between(start_date, end_date):
    months = []

    current_year = start_date.year
    current_month = start_date.month

    while (
        current_year < end_date.year
        or (
            current_year == end_date.year
            and current_month <= end_date.month
        )
    ):
        months.append((current_year, current_month))

        if current_month == 12:
            current_year += 1
            current_month = 1
        else:
            current_month += 1

    return months


def get_report_chart(
    *,
    walks,
    period,
    start_date,
    end_date,
):
    Period = ReportPeriodQuerySerializer.Period

    if period == Period.DAY:
        buckets = [
            create_empty_bucket(
                f"{hour:02d}~{hour + 4:02d}시"
            )
            for hour in range(0, 24, 4)
        ]

        for walk in walks:
            local_end_time = timezone.localtime(
                walk.end_time
            )
            bucket_index = local_end_time.hour // 4

            add_walk_to_bucket(
                buckets[bucket_index],
                walk,
            )

    elif period == Period.WEEK:
        weekday_labels = [
            "월",
            "화",
            "수",
            "목",
            "금",
            "토",
            "일",
        ]

        buckets = [
            create_empty_bucket(label)
            for label in weekday_labels
        ]

        for walk in walks:
            walk_date = timezone.localdate(
                walk.end_time
            )
            bucket_index = walk_date.weekday()

            add_walk_to_bucket(
                buckets[bucket_index],
                walk,
            )

    elif period == Period.MONTH:
        week_count = (end_date.day - 1) // 7 + 1

        buckets = [
            create_empty_bucket(f"{week}주차")
            for week in range(1, week_count + 1)
        ]

        for walk in walks:
            walk_date = timezone.localdate(
                walk.end_time
            )
            bucket_index = (walk_date.day - 1) // 7

            add_walk_to_bucket(
                buckets[bucket_index],
                walk,
            )

    elif period == Period.SIX_MONTHS:
        months = get_months_between(
            start_date,
            end_date,
        )

        buckets = [
            create_empty_bucket(f"{month}월")
            for year, month in months
        ]

        month_indexes = {
            (year, month): index
            for index, (year, month) in enumerate(months)
        }

        for walk in walks:
            walk_date = timezone.localdate(
                walk.end_time
            )

            bucket_index = month_indexes[
                (walk_date.year, walk_date.month)
            ]

            add_walk_to_bucket(
                buckets[bucket_index],
                walk,
            )

    elif period == Period.YEAR:
        buckets = [
            create_empty_bucket(f"{month}월")
            for month in range(1, 13)
        ]

        for walk in walks:
            walk_date = timezone.localdate(
                walk.end_time
            )
            bucket_index = walk_date.month - 1

            add_walk_to_bucket(
                buckets[bucket_index],
                walk,
            )

    else:
        raise ValueError(
            "지원하지 않는 리포트 기간입니다."
        )

    for bucket in buckets:
        bucket["distance_km"] = round(
            bucket["distance_km"],
            2,
        )

    return buckets


def get_growth_report(*, pet, start_date, end_date):
    current_timezone = timezone.get_current_timezone()

    start_datetime = timezone.make_aware(
        datetime.combine(start_date, time.min),
        timezone=current_timezone,
    )

    end_exclusive_datetime = timezone.make_aware(
        datetime.combine(
            end_date + timedelta(days=1),
            time.min,
        ),
        timezone=current_timezone,
    )

    histories = (
        PetHistory.objects
        .filter(
            pet=pet,
            created_at__gte=start_datetime,
            created_at__lt=end_exclusive_datetime,
        )
        .order_by("created_at")
    )

    return {
        "level_up_count": histories.count(),
        "histories": [
            {
                "before_level": history.before_level,
                "after_level": history.after_level,
                "created_at": history.created_at,
            }
            for history in histories
        ],
    }


def get_earned_badges(*, pet, start_date, end_date):
    current_timezone = timezone.get_current_timezone()

    start_datetime = timezone.make_aware(
        datetime.combine(start_date, time.min),
        timezone=current_timezone,
    )

    end_exclusive_datetime = timezone.make_aware(
        datetime.combine(
            end_date + timedelta(days=1),
            time.min,
        ),
        timezone=current_timezone,
    )

    pet_badges = (
        PetBadge.objects
        .select_related("badge")
        .filter(
            pet=pet,
            acquired_at__gte=start_datetime,
            acquired_at__lt=end_exclusive_datetime,
        )
        .order_by("acquired_at")
    )

    return [
        {
            "badge_id": pet_badge.badge_id,
            "name": pet_badge.badge.name,
            "acquired_at": pet_badge.acquired_at,
        }
        for pet_badge in pet_badges
    ]
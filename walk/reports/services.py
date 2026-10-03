from calendar import monthrange
from datetime import date, datetime, time, timedelta

from django.utils import timezone

from walk.models import WalkingSession
from walk.reports.serializers import ComparisonType, ReportPeriod


DAILY_AVERAGE_DAYS = 28


# 하루 시간대 구분
DAYPARTS = [
    {
        "key": "MORNING",
        "label": "아침",
        "start_hour": 6,
        "end_hour": 12,
    },
    {
        "key": "LUNCH",
        "label": "점심",
        "start_hour": 12,
        "end_hour": 14,
    },
    {
        "key": "AFTERNOON",
        "label": "오후",
        "start_hour": 14,
        "end_hour": 18,
    },
    {
        "key": "EVENING",
        "label": "저녁",
        "start_hour": 18,
        "end_hour": 6,
    },
]


# 선택한 날짜를 기준으로 현재 리포트의 조회 범위 반환
def get_report_date_range(*, period, anchor_date):
    today = timezone.localdate()

    if period == ReportPeriod.DAY:
        return anchor_date, anchor_date

    if period == ReportPeriod.MONTH:
        start_date = anchor_date.replace(
            day=1,
        )

        last_day = monthrange(
            anchor_date.year,
            anchor_date.month,
        )[1]

        end_date = anchor_date.replace(
            day=last_day,
        )

        if (
            anchor_date.year == today.year
            and anchor_date.month == today.month
        ):
            end_date = today

        return start_date, end_date

    if period == ReportPeriod.YEAR:
        start_date = date(
            anchor_date.year,
            1,
            1,
        )

        end_date = date(
            anchor_date.year,
            12,
            31,
        )

        if anchor_date.year == today.year:
            end_date = today

        return start_date, end_date

    raise ValueError(
        "지원하지 않는 리포트 기간입니다."
    )


# 현재 리포트와 비교할 기간 반환
def get_comparison_date_range(
    *,
    period,
    start_date,
    end_date,
):
    today = timezone.localdate()

    if period == ReportPeriod.DAY:
        comparison_end = (
            start_date - timedelta(days=1)
        )

        comparison_start = (
            comparison_end
            - timedelta(
                days=DAILY_AVERAGE_DAYS - 1,
            )
        )

        return (
            comparison_start,
            comparison_end,
        )

    if period == ReportPeriod.MONTH:
        previous_month_end = (
            start_date - timedelta(days=1)
        )

        previous_month_start = (
            previous_month_end.replace(day=1)
        )

        is_current_month = (
            start_date.year == today.year
            and start_date.month == today.month
        )

        if not is_current_month:
            return (
                previous_month_start,
                previous_month_end,
            )

        elapsed_days = (
            end_date - start_date
        ).days + 1

        comparison_end = min(
            previous_month_start
            + timedelta(days=elapsed_days - 1),
            previous_month_end,
        )

        return (
            previous_month_start,
            comparison_end,
        )

    if period == ReportPeriod.YEAR:
        previous_year = start_date.year - 1

        comparison_start = date(
            previous_year,
            1,
            1,
        )

        is_current_year = (
            start_date.year == today.year
        )

        if not is_current_year:
            comparison_end = date(
                previous_year,
                12,
                31,
            )

            return (
                comparison_start,
                comparison_end,
            )

        comparison_day = min(
            end_date.day,
            monthrange(
                previous_year,
                end_date.month,
            )[1],
        )

        comparison_end = date(
            previous_year,
            end_date.month,
            comparison_day,
        )

        return (
            comparison_start,
            comparison_end,
        )

    raise ValueError(
        "지원하지 않는 리포트 기간입니다."
    )


# 해당 기간에 시작된 완료 산책 기록 반환
def get_completed_walks(
    *,
    pet,
    start_date,
    end_date,
):
    current_timezone = (
        timezone.get_current_timezone()
    )

    start_datetime = timezone.make_aware(
        datetime.combine(
            start_date,
            time.min,
        ),
        timezone=current_timezone,
    )

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
            start_time__gte=start_datetime,
            start_time__lt=end_exclusive_datetime,
        )
        .only(
            "id",
            "start_time",
            "end_time",
            "total_distance",
            "total_duration",
        )
        .order_by("start_time")
    )


# 산책 목록의 총 거리 계산
def get_total_distance(walks):
    return round(
        sum(
            float(walk.total_distance or 0)
            for walk in walks
        ),
        2,
    )


# 기간별 거리 비교 데이터 반환
def get_distance_comparison(
    *,
    period,
    current_walks,
    comparison_walks,
):
    current_distance = get_total_distance(
        current_walks
    )

    comparison_distance = get_total_distance(
        comparison_walks
    )

    if period == ReportPeriod.DAY:
        baseline_distance = round(
            comparison_distance
            / DAILY_AVERAGE_DAYS,
            2,
        )

        baseline_type = (
            ComparisonType.RECENT_AVERAGE
        )

    elif period == ReportPeriod.MONTH:
        baseline_distance = comparison_distance

        baseline_type = (
            ComparisonType.PREVIOUS_MONTH
        )

    elif period == ReportPeriod.YEAR:
        baseline_distance = comparison_distance

        baseline_type = (
            ComparisonType.PREVIOUS_YEAR
        )

    else:
        raise ValueError(
            "지원하지 않는 리포트 기간입니다."
        )

    difference = round(
        current_distance - baseline_distance,
        2,
    )

    return {
        "current_distance_km": current_distance,
        "baseline_distance_km": baseline_distance,
        "difference_km": difference,
        "baseline_type": baseline_type,
    }


# 그래프 항목 생성
def create_trend_item(
    *,
    key,
    label,
    distance_km=0,
):
    return {
        "key": key,
        "label": label,
        "distance_km": round(
            float(distance_km),
            2,
        ),
    }


# 하루 시간별 그래프 데이터 생성
def get_daily_trend(
    *,
    current_walks,
    comparison_walks,
):
    current_distances = [
        0.0
        for _ in range(24)
    ]

    comparison_distances = [
        0.0
        for _ in range(24)
    ]

    for walk in current_walks:
        local_start_time = timezone.localtime(
            walk.start_time
        )

        current_distances[
            local_start_time.hour
        ] += float(
            walk.total_distance or 0
        )

    for walk in comparison_walks:
        local_start_time = timezone.localtime(
            walk.start_time
        )

        comparison_distances[
            local_start_time.hour
        ] += float(
            walk.total_distance or 0
        )

    current = []
    comparison = []

    for hour in range(24):
        current.append(
            create_trend_item(
                key=hour,
                label=f"{hour}시",
                distance_km=current_distances[
                    hour
                ],
            )
        )

        comparison.append(
            create_trend_item(
                key=hour,
                label=f"{hour}시",
                distance_km=(
                    comparison_distances[hour]
                    / DAILY_AVERAGE_DAYS
                ),
            )
        )

    return {
        "current": current,
        "comparison": comparison,
    }


# 월간 일별 그래프 데이터 생성
def get_monthly_trend(
    *,
    current_walks,
    comparison_walks,
    start_date,
    comparison_start_date,
):
    current_last_day = monthrange(
        start_date.year,
        start_date.month,
    )[1]

    comparison_last_day = monthrange(
        comparison_start_date.year,
        comparison_start_date.month,
    )[1]

    max_day = max(
        current_last_day,
        comparison_last_day,
    )

    current_distances = [
        0.0
        for _ in range(max_day)
    ]

    comparison_distances = [
        0.0
        for _ in range(max_day)
    ]

    for walk in current_walks:
        walk_date = timezone.localdate(
            walk.start_time
        )

        current_distances[
            walk_date.day - 1
        ] += float(
            walk.total_distance or 0
        )

    for walk in comparison_walks:
        walk_date = timezone.localdate(
            walk.start_time
        )

        comparison_distances[
            walk_date.day - 1
        ] += float(
            walk.total_distance or 0
        )

    current = []
    comparison = []

    for day in range(1, max_day + 1):
        current.append(
            create_trend_item(
                key=day,
                label=f"{day}일",
                distance_km=(
                    current_distances[day - 1]
                    if day <= current_last_day
                    else 0
                ),
            )
        )

        comparison.append(
            create_trend_item(
                key=day,
                label=f"{day}일",
                distance_km=(
                    comparison_distances[day - 1]
                    if day <= comparison_last_day
                    else 0
                ),
            )
        )

    return {
        "current": current,
        "comparison": comparison,
    }


# 연간 월별 그래프 데이터 생성
def get_yearly_trend(
    *,
    current_walks,
    comparison_walks,
):
    current_distances = [
        0.0
        for _ in range(12)
    ]

    comparison_distances = [
        0.0
        for _ in range(12)
    ]

    for walk in current_walks:
        walk_date = timezone.localdate(
            walk.start_time
        )

        current_distances[
            walk_date.month - 1
        ] += float(
            walk.total_distance or 0
        )

    for walk in comparison_walks:
        walk_date = timezone.localdate(
            walk.start_time
        )

        comparison_distances[
            walk_date.month - 1
        ] += float(
            walk.total_distance or 0
        )

    current = []
    comparison = []

    for month in range(1, 13):
        current.append(
            create_trend_item(
                key=month,
                label=f"{month}월",
                distance_km=current_distances[
                    month - 1
                ],
            )
        )

        comparison.append(
            create_trend_item(
                key=month,
                label=f"{month}월",
                distance_km=comparison_distances[
                    month - 1
                ],
            )
        )

    return {
        "current": current,
        "comparison": comparison,
    }


# 기간에 맞는 그래프 데이터 반환
def get_trend_data(
    *,
    period,
    current_walks,
    comparison_walks,
    start_date,
    comparison_start_date,
):
    if period == ReportPeriod.DAY:
        return get_daily_trend(
            current_walks=current_walks,
            comparison_walks=comparison_walks,
        )

    if period == ReportPeriod.MONTH:
        return get_monthly_trend(
            current_walks=current_walks,
            comparison_walks=comparison_walks,
            start_date=start_date,
            comparison_start_date=(
                comparison_start_date
            ),
        )

    if period == ReportPeriod.YEAR:
        return get_yearly_trend(
            current_walks=current_walks,
            comparison_walks=comparison_walks,
        )

    raise ValueError(
        "지원하지 않는 리포트 기간입니다."
    )


# 시간대에 해당하는 키 반환
def get_daypart_key(hour):
    for daypart in DAYPARTS:
        start_hour = daypart[
            "start_hour"
        ]
        end_hour = daypart[
            "end_hour"
        ]

        if start_hour < end_hour:
            if (
                start_hour
                <= hour
                < end_hour
            ):
                return daypart["key"]

        else:
            if (
                hour >= start_hour
                or hour < end_hour
            ):
                return daypart["key"]

    return None


# 하루 시간대별 통계 생성
def get_daily_highlight(walks):
    distances = {
        daypart["key"]: 0.0
        for daypart in DAYPARTS
    }

    for walk in walks:
        local_start_time = timezone.localtime(
            walk.start_time
        )

        daypart_key = get_daypart_key(
            local_start_time.hour
        )

        if daypart_key:
            distances[daypart_key] += float(
                walk.total_distance or 0
            )

    items = [
        {
            "key": daypart["key"],
            "label": daypart["label"],
            "distance_km": round(
                distances[daypart["key"]],
                2,
            ),
        }
        for daypart in DAYPARTS
    ]

    return build_highlight_result(items)


# 월간 주차별 통계 생성
def get_monthly_highlight(walks):
    distances = [
        0.0,
        0.0,
        0.0,
        0.0,
    ]

    for walk in walks:
        walk_date = timezone.localdate(
            walk.start_time
        )

        week_index = min(
            (walk_date.day - 1) // 7,
            3,
        )

        distances[week_index] += float(
            walk.total_distance or 0
        )

    items = [
        {
            "key": str(index),
            "label": f"{index}주",
            "distance_km": round(
                distances[index - 1],
                2,
            ),
        }
        for index in range(1, 5)
    ]

    return build_highlight_result(items)


# 연간 월별 통계 생성
def get_yearly_highlight(walks):
    distances = [
        0.0
        for _ in range(12)
    ]

    for walk in walks:
        walk_date = timezone.localdate(
            walk.start_time
        )

        distances[
            walk_date.month - 1
        ] += float(
            walk.total_distance or 0
        )

    items = [
        {
            "key": str(month),
            "label": f"{month}월",
            "distance_km": round(
                distances[month - 1],
                2,
            ),
        }
        for month in range(1, 13)
    ]

    return build_highlight_result(items)


# 가장 많이 걸은 구간 계산
def build_highlight_result(items):
    if not items:
        return {
            "top_label": None,
            "top_distance_km": 0.0,
            "items": [],
        }

    top_item = max(
        items,
        key=lambda item: item[
            "distance_km"
        ],
    )

    if top_item["distance_km"] == 0:
        top_label = None
    else:
        top_label = top_item["label"]

    return {
        "top_label": top_label,
        "top_distance_km": (
            top_item["distance_km"]
        ),
        "items": items,
    }


# 기간에 맞는 하이라이트 통계 반환
def get_highlight_data(
    *,
    period,
    walks,
):
    if period == ReportPeriod.DAY:
        return get_daily_highlight(
            walks
        )

    if period == ReportPeriod.MONTH:
        return get_monthly_highlight(
            walks
        )

    if period == ReportPeriod.YEAR:
        return get_yearly_highlight(
            walks
        )

    raise ValueError(
        "지원하지 않는 리포트 기간입니다."
    )


# 산책 리포트 전체 데이터 생성
def build_walk_report(
    *,
    pet,
    period,
    anchor_date,
):
    start_date, end_date = (
        get_report_date_range(
            period=period,
            anchor_date=anchor_date,
        )
    )

    comparison_start_date, comparison_end_date = (
        get_comparison_date_range(
            period=period,
            start_date=start_date,
            end_date=end_date,
        )
    )

    current_walks = list(
        get_completed_walks(
            pet=pet,
            start_date=start_date,
            end_date=end_date,
        )
    )

    comparison_walks = list(
        get_completed_walks(
            pet=pet,
            start_date=(
                comparison_start_date
            ),
            end_date=(
                comparison_end_date
            ),
        )
    )

    return {
        "pet_id": pet.id,
        "period": period,
        "date": anchor_date,
        "start_date": start_date,
        "end_date": end_date,
        "comparison": get_distance_comparison(
            period=period,
            current_walks=current_walks,
            comparison_walks=(
                comparison_walks
            ),
        ),
        "trend": get_trend_data(
            period=period,
            current_walks=current_walks,
            comparison_walks=(
                comparison_walks
            ),
            start_date=start_date,
            comparison_start_date=(
                comparison_start_date
            ),
        ),
        "highlight": get_highlight_data(
            period=period,
            walks=current_walks,
        ),
    }
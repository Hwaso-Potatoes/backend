from django.db.models import Q
from django.utils import timezone
from geopy.distance import geodesic

from .models import WalkingPath


# ─────────────────────────────────────────────
# 경험치 (기존 develop 코드 유지)
# ─────────────────────────────────────────────
MAX_WALK_EXPERIENCE = 50
EXPERIENCE_PER_KM = 10


def calculate_walk_experience(distance_km):
    if distance_km <= 0:
        return 0

    experience = int(distance_km * EXPERIENCE_PER_KM)

    return min(experience, MAX_WALK_EXPERIENCE)


# ─────────────────────────────────────────────
# 위치 경로 저장 (REST / WebSocket 공통)
# ─────────────────────────────────────────────
MAX_JUMP_KM = 0.1          # 연속된 두 점 사이 허용 거리 (100m)
MIN_MOVE_KM = 0.001        # 1m 미만 이동은 거리 누적 안 함
MAX_SPEED_MPS = 4.0        # 반려견 산책 최대 속도 (초속 4m ≈ 시속 14km)
COUNT_GAP_DISTANCE = False # 공백 후 재기준점 잡을 때 그 사이 거리를 누적할지


def get_last_path(session):
    return session.paths.order_by('-recorded_at', '-id').first()


def _clamp_time(recorded_at, session, now):
    """기기 시계 오차 보정: [산책 시작, 현재] 범위로 맞춤. 미전송이면 현재 시각"""
    if recorded_at is None or recorded_at > now:
        return now
    if recorded_at < session.start_time:
        return session.start_time
    return recorded_at


def _is_plausible_move(dist_km, elapsed_seconds):
    """경과 시간 대비 이동 거리가 걸어서 가능한 속도인지"""
    if elapsed_seconds <= 0:
        return False
    return (dist_km * 1000) / elapsed_seconds <= MAX_SPEED_MPS


def append_locations(session, locations):
    """
    검증된 좌표 목록을 경로에 추가하고 누적 거리를 갱신.
    호출부에서 transaction.atomic + select_for_update로 session을 잠근 상태여야 함.
    반환값: 실제 저장된 WalkingPath 리스트 (측정 시각순)
    """
    now = timezone.now()

    # 측정 시각 보정 후 시간순 정렬 (배치 안 순서가 섞여 와도 거리 계산이 맞도록)
    points = sorted(
        (
            {**loc, 'recorded_at': _clamp_time(loc.get('recorded_at'), session, now)}
            for loc in locations
        ),
        key=lambda p: p['recorded_at'],
    )

    last_path = get_last_path(session)
    if last_path:
        anchor_coords = (float(last_path.latitude), float(last_path.longitude))
        anchor_time = last_path.recorded_at or last_path.timestamp
    else:
        anchor_coords = None
        anchor_time = None

    created_paths = []
    added_distance_km = 0.0

    for p in points:
        current_coords = (float(p['latitude']), float(p['longitude']))

        if anchor_coords:
            dist_km = geodesic(anchor_coords, current_coords).km

            if dist_km > MAX_JUMP_KM:
                elapsed = (p['recorded_at'] - anchor_time).total_seconds()
                if _is_plausible_move(dist_km, elapsed):
                    # 실제 이동(백그라운드 공백, 일시정지 후 재개 등) → 새 기준점
                    if COUNT_GAP_DISTANCE:
                        added_distance_km += dist_km
                    anchor_coords, anchor_time = current_coords, p['recorded_at']
                else:
                    continue    # GPS 튐으로 판단, 버림
            elif dist_km >= MIN_MOVE_KM:
                added_distance_km += dist_km
                anchor_coords, anchor_time = current_coords, p['recorded_at']
        else:
            anchor_coords, anchor_time = current_coords, p['recorded_at']

        created_paths.append(WalkingPath(
            session=session,
            latitude=p['latitude'],
            longitude=p['longitude'],
            recorded_at=p['recorded_at'],
        ))

    if created_paths:
        WalkingPath.objects.bulk_create(created_paths)

    if added_distance_km > 0:
        session.total_distance += added_distance_km
        session.save(update_fields=['total_distance'])

    return created_paths


# ─────────────────────────────────────────────
# 친구 정보 (근처 친구 목록 / 친구 알림용)
# ─────────────────────────────────────────────
def get_friend_ids(user_id):
    """수락된 친구들의 user id 집합 (요청 방향 무관)"""
    from friends.models import Friend

    rows = Friend.objects.filter(status=Friend.Status.ACCEPTED).filter(
        Q(requester_id=user_id) | Q(receiver_id=user_id)
    ).values_list('requester_id', 'receiver_id')
    return {rec if req == user_id else req for req, rec in rows}


def get_walker_profile(session):
    """친구 목록에 보여줄 산책자 정보"""
    return {
        "nickname": getattr(session.user, 'nickname', None),
        "pet_name": session.pet.name if session.pet else None,
    }

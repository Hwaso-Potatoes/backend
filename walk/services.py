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
    # 같은 배치(bulk_create)는 timestamp가 동일하므로 id로 순서 보장
    return session.paths.order_by('-timestamp', '-id').first()


def _is_plausible_move(dist_km, elapsed_seconds):
    """경과 시간 대비 이동 거리가 걸어서 가능한 속도인지"""
    if elapsed_seconds <= 0:
        return False
    return (dist_km * 1000) / elapsed_seconds <= MAX_SPEED_MPS


def append_locations(session, locations):
    """
    검증된 좌표 목록을 경로에 추가하고 누적 거리를 갱신.
    호출부에서 transaction.atomic + select_for_update로 session을 잠근 상태여야 함.
    반환값: 실제 저장된 WalkingPath 리스트
    """
    last_path = get_last_path(session)
    last_coords = (float(last_path.latitude), float(last_path.longitude)) if last_path else None
    elapsed_since_last = (
        (timezone.now() - last_path.timestamp).total_seconds() if last_path else 0
    )

    created_paths = []
    added_distance_km = 0.0

    for i, loc in enumerate(locations):
        current_coords = (float(loc['latitude']), float(loc['longitude']))

        if last_coords:
            dist_km = geodesic(last_coords, current_coords).km

            if dist_km > MAX_JUMP_KM:
                # 배치의 첫 점만 '마지막 저장 시각' 기준으로 실제 이동 여부 판단
                # (백그라운드 공백 / 일시정지 후 재개 등)
                if i == 0 and _is_plausible_move(dist_km, elapsed_since_last):
                    if COUNT_GAP_DISTANCE:
                        added_distance_km += dist_km
                    last_coords = current_coords   # 새 기준점
                else:
                    continue                       # GPS 튐으로 판단, 버림
            elif dist_km >= MIN_MOVE_KM:
                added_distance_km += dist_km
                last_coords = current_coords
        else:
            last_coords = current_coords

        created_paths.append(WalkingPath(
            session=session,
            latitude=loc['latitude'],
            longitude=loc['longitude'],
        ))

    if created_paths:
        WalkingPath.objects.bulk_create(created_paths)

    if added_distance_km > 0:
        session.total_distance += added_distance_km
        session.save(update_fields=['total_distance'])

    return created_paths
"""
산책 위치 유형 판정 (숲 / 도시 / 새로운 지역)

- 숲 산책: 경로에서 연속된 점 3개 이상이 숲·공원 영역 안
- 도시 산책: 경로에서 연속된 점 3개 이상이 숲·공원 영역 밖
- 새로운 지역: 이번 경로가 지나간 약 200m 격자 칸 중 절반 이상이 처음 가본 칸

숲·공원 영역은 OpenStreetMap(Overpass API)에서 약 5km 타일 단위로 한 번만 받아 DB에 저장한다.
→ 외부 호출은 '처음 가보는 타일 수'만큼만 발생하고, 사용자 좌표는 외부로 보내지 않는다(타일 범위만 전송).
"""
import logging
import math
import threading
from datetime import timedelta

import requests
from django.db import connection
from django.utils import timezone
from shapely import STRtree, make_valid
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import linemerge, polygonize

from .models import GreenAreaTile, VisitedCell, WalkingSession

logger = logging.getLogger(__name__)

# ── 판정 기준 ─────────────────────────────────
FOREST_MIN_CONSECUTIVE = 3        # 숲·공원 안 연속 점 개수
CITY_MIN_CONSECUTIVE = 3          # 숲·공원 밖 연속 점 개수
NEW_AREA_MIN_RATIO = 0.5          # 처음 가본 격자 칸 비율
NEW_AREA_REQUIRE_HISTORY = True   # 첫 산책은 '새로운 지역'으로 치지 않음

# 숲·공원으로 볼 OSM 태그
GREEN_TAGS = [
    ('landuse', 'forest'),
    ('natural', 'wood'),
    ('leisure', 'park'),
]

# ── 격자 크기 ─────────────────────────────────
TILE_DEG = 0.05                   # 숲·공원 데이터 조회 단위 (약 5km)
TILE_RETRY_AFTER = timedelta(hours=1)
CELL_LAT_DEG = 0.002              # 새로운 지역 판정 단위 (약 200m)
CELL_LNG_DEG = 0.0025

# ── 외부 API ─────────────────────────────────
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_TIMEOUT = 60
USER_AGENT = "WalkGuide/1.0 (Hwaso-Potatoes backend)"

# 프로세스 내 캐시: tile_key → (STRtree, polygons)
_tile_cache = {}
_cache_lock = threading.Lock()


# ─────────────────────────────────────────────
# 타일 / 격자 키
# ─────────────────────────────────────────────
def tile_key(lat, lng):
    return f"{math.floor(lat / TILE_DEG)}:{math.floor(lng / TILE_DEG)}"


def tile_bbox(key):
    """(south, west, north, east)"""
    i, j = map(int, key.split(':'))
    return (i * TILE_DEG, j * TILE_DEG, (i + 1) * TILE_DEG, (j + 1) * TILE_DEG)


def cell_key(lat, lng):
    return f"{math.floor(lat / CELL_LAT_DEG)}:{math.floor(lng / CELL_LNG_DEG)}"


# ─────────────────────────────────────────────
# OSM 숲·공원 영역 조회
# ─────────────────────────────────────────────
def _fetch_green_rings(bbox):
    south, west, north, east = bbox
    b = f"{south},{west},{north},{east}"
    parts = "".join(
        f'way["{k}"="{v}"]({b});relation["{k}"="{v}"]({b});' for k, v in GREEN_TAGS
    )
    query = f"[out:json][timeout:{OVERPASS_TIMEOUT - 10}];({parts});out geom;"

    resp = requests.post(
        OVERPASS_URL,
        data={'data': query},
        timeout=OVERPASS_TIMEOUT,
        headers={'User-Agent': USER_AGENT},
    )
    resp.raise_for_status()
    return _elements_to_rings(resp.json().get('elements', []))


def _elements_to_rings(elements):
    """OSM 요소 → 다각형 외곽선 좌표 목록 [[ [lng, lat], ... ], ...]"""
    rings = []
    for el in elements:
        if el.get('type') == 'way':
            coords = [(p['lon'], p['lat']) for p in el.get('geometry', [])]
            if len(coords) >= 4 and coords[0] == coords[-1]:
                rings.append(coords)

        elif el.get('type') == 'relation':
            # 멀티폴리곤: outer 조각들을 이어 붙여 다각형으로 (inner 구멍은 무시)
            lines = [
                LineString([(p['lon'], p['lat']) for p in m['geometry']])
                for m in el.get('members', [])
                if m.get('type') == 'way'
                and m.get('role') in ('outer', '')
                and len(m.get('geometry', [])) >= 2
            ]
            if not lines:
                continue
            merged = linemerge(lines)
            for poly in polygonize(getattr(merged, 'geoms', [merged])):
                rings.append(list(poly.exterior.coords))

    return [[list(c) for c in ring] for ring in rings]


def _build_index(rings):
    polys = []
    for ring in rings:
        try:
            geom = make_valid(Polygon(ring))
        except Exception:
            continue
        if not geom.is_empty:
            polys.append(geom)
    return STRtree(polys), polys


def _get_tile_index(key):
    """타일의 숲·공원 공간 인덱스. 데이터를 못 구하면 None."""
    with _cache_lock:
        if key in _tile_cache:
            return _tile_cache[key]

    tile = GreenAreaTile.objects.filter(key=key).first()
    now = timezone.now()

    need_fetch = tile is None or (not tile.is_ok and now - tile.fetched_at > TILE_RETRY_AFTER)
    if need_fetch:
        try:
            rings = _fetch_green_rings(tile_bbox(key))
        except Exception:
            logger.exception("숲/공원 데이터 조회 실패 (tile=%s)", key)
            GreenAreaTile.objects.update_or_create(
                key=key, defaults={'polygons': [], 'is_ok': False, 'fetched_at': now}
            )
            return None
        tile, _ = GreenAreaTile.objects.update_or_create(
            key=key, defaults={'polygons': rings, 'is_ok': True, 'fetched_at': now}
        )
    elif not tile.is_ok:
        return None   # 최근에 실패한 타일 → 재시도 대기

    index = _build_index(tile.polygons)
    with _cache_lock:
        _tile_cache[key] = index
    return index


def _in_green(index, lat, lng):
    tree, _ = index
    return len(tree.query(Point(lng, lat), predicate='intersects')) > 0


# ─────────────────────────────────────────────
# 판정
# ─────────────────────────────────────────────
def _has_run(flags, value, n):
    run = 0
    for flag in flags:
        run = run + 1 if flag == value else 0
        if run >= n:
            return True
    return False


def _check_new_area(user_id, coords):
    cells = {cell_key(lat, lng) for lat, lng in coords}
    if not cells:
        return False

    has_history = VisitedCell.objects.filter(user_id=user_id).exists()
    visited = set(
        VisitedCell.objects.filter(user_id=user_id, cell_key__in=cells)
        .values_list('cell_key', flat=True)
    )
    new_ratio = (len(cells) - len(visited)) / len(cells)

    VisitedCell.objects.bulk_create(
        [VisitedCell(user_id=user_id, cell_key=c) for c in cells - visited],
        ignore_conflicts=True,
    )

    if NEW_AREA_REQUIRE_HISTORY and not has_history:
        return False
    return new_ratio >= NEW_AREA_MIN_RATIO


def _result(session):
    return {
        'is_forest_walk': session.is_forest_walk,
        'is_city_walk': session.is_city_walk,
        'is_new_area': session.is_new_area,
    }


def classify_walk(session_id, force=False):
    """
    산책 위치 유형을 판정해서 WalkingSession에 저장하고 결과를 반환.
    숲/도시는 지도 데이터를 못 구하면 None(판정 불가)으로 남는다.
    force=True면 숲/도시를 다시 판정한다. (새로운 지역은 방문 기록이 쌓여서 최초 값 유지)
    """
    session = WalkingSession.objects.get(id=session_id)
    if session.classified_at and not force:
        return _result(session)

    coords = [
        (float(lat), float(lng))
        for lat, lng in session.paths.order_by('recorded_at', 'id').values_list('latitude', 'longitude')
    ]

    # 숲 / 도시
    is_forest = is_city = None
    flags = []
    for lat, lng in coords:
        index = _get_tile_index(tile_key(lat, lng))
        if index is None:
            flags = None
            break
        flags.append(_in_green(index, lat, lng))
    if flags is not None:
        is_forest = _has_run(flags, True, FOREST_MIN_CONSECUTIVE)
        is_city = _has_run(flags, False, CITY_MIN_CONSECUTIVE)

    # 새로운 지역 (재판정 시에는 최초 값 유지)
    if session.classified_at and session.is_new_area is not None:
        is_new = session.is_new_area
    else:
        is_new = _check_new_area(session.user_id, coords)

    WalkingSession.objects.filter(id=session.id).update(
        is_forest_walk=is_forest,
        is_city_walk=is_city,
        is_new_area=is_new,
        classified_at=timezone.now(),
    )
    session.refresh_from_db()
    return _result(session)


def classify_walk_in_background(session_id):
    """외부 지도 조회가 있어서 산책 종료 응답을 막지 않도록 별도 스레드에서 실행"""
    def _run():
        try:
            result = classify_walk(session_id)
            from .signals import send_walk_classified
            send_walk_classified(session_id, result)
        except Exception:
            logger.exception("산책 위치 유형 판정 실패 (walk_id=%s)", session_id)
        finally:
            connection.close()

    threading.Thread(target=_run, daemon=True).start()

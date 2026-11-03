import json
import math
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import transaction
from geopy.distance import geodesic

from .models import WalkingSession, WalkPreference
from .serializers import WalkingPathBatchSerializer
from .services import append_locations, get_last_path, get_friend_ids, get_walker_profile
from .realtime import walk_group, user_group

ACTIVE_STATUSES = ('WALKING', 'PAUSED')

# 종료 코드
CLOSE_UNAUTHENTICATED = 4001
CLOSE_FORBIDDEN = 4003
CLOSE_NOT_FOUND = 4004   # 없는 세션 또는 이미 종료된 산책

# 근처 친구 반경 (km)
DEFAULT_RADIUS_KM = 5.0
MAX_RADIUS_KM = 10.0


def are_friends(user_id, other_user_id):
    """수락된 친구 관계인지 (요청 방향 무관)"""
    return other_user_id in get_friend_ids(user_id)


def _parse_radius(value, default):
    try:
        radius = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(radius) or radius <= 0:
        return default
    return min(radius, MAX_RADIUS_KM)


def _parse_coords(data):
    try:
        lat = float(data.get('latitude'))
        lng = float(data.get('longitude'))
    except (TypeError, ValueError, AttributeError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lng)):
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return (lat, lng)


async def _send_error(consumer, message, detail=None):
    payload = {"type": "error", "message": message}
    if detail is not None:
        payload["detail"] = detail
    await consumer.send(text_data=json.dumps(payload, ensure_ascii=False))


# ═════════════════════════════════════════════
# 산책방: ws/walks/<walk_id>/
# ═════════════════════════════════════════════
class WalkConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.walk_id = self.scope['url_route']['kwargs']['walk_id']
        self.room_group_name = walk_group(self.walk_id)
        self.user = self.scope.get('user', None)
        self.role = None       # 'owner' | 'friend'
        self.joined = False
        self.fanout_groups = []
        self.profile = {}

        if not self.user or not getattr(self.user, 'is_authenticated', False):
            await self.close(code=CLOSE_UNAUTHENTICATED)
            return

        access = await self.check_access()
        if access is None:
            await self.close(code=CLOSE_NOT_FOUND)
            return

        role, snapshot = access
        if role is None:
            await self.close(code=CLOSE_FORBIDDEN)
            return

        self.role = role
        if role == 'owner':
            # 근처 친구 목록 갱신용: 친구들 개인 채널 + 내 표시 정보 (접속 시 1회만 조회)
            self.fanout_groups, self.profile = await self.load_owner_context()

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        self.joined = True
        await self.accept()

        # 친구가 접속하면 공유 중인 마지막 좌표를 바로 1회 전송
        if snapshot:
            await self.send(text_data=json.dumps({"type": "location", **snapshot}))

    async def disconnect(self, close_code):
        if self.joined:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if self.role != 'owner':
            await _send_error(self, "좌표 전송은 산책 주인만 할 수 있습니다.")
            return

        try:
            data = json.loads(text_data or '')
        except json.JSONDecodeError:
            await _send_error(self, "JSON 형식이 아닙니다.")
            return

        result = await self.process_location(data)
        if 'error' in result:
            await _send_error(self, result['error'], result.get('detail'))
            return

        # 공유 On이고 실제로 저장된 좌표가 있을 때만 브로드캐스트 (튄 좌표는 전송 안 함)
        if result['is_location_shared'] and result['latest']:
            lat, lng = result['latest']

            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'walk_location',
                'user_id': self.user.id,
                'walk_id': int(self.walk_id),
                'latitude': lat,
                'longitude': lng,
            })

            friend_event = {
                'type': 'friend_location',
                'user_id': self.user.id,
                'walk_id': int(self.walk_id),
                **self.profile,
                'latitude': lat,
                'longitude': lng,
            }
            for group in self.fanout_groups:
                await self.channel_layer.group_send(group, friend_event)

    # ── 그룹 이벤트 핸들러 ──────────────────────────
    async def walk_location(self, event):
        await self.send(text_data=json.dumps({
            'type': 'location',
            'user_id': event['user_id'],
            'walk_id': event.get('walk_id'),
            'latitude': event['latitude'],
            'longitude': event['longitude'],
        }))

    async def walk_location_hidden(self, event):
        await self.send(text_data=json.dumps({
            'type': 'location_hidden',
            'user_id': event['user_id'],
            'walk_id': event.get('walk_id'),
            'reason': event.get('reason'),
        }))

    # ── DB ───────────────────────────────────────
    @database_sync_to_async
    def check_access(self):
        """None: 세션 없음/종료, (None, None): 권한 없음, (role, snapshot): 허용"""
        try:
            session = WalkingSession.objects.get(id=self.walk_id)
        except (WalkingSession.DoesNotExist, ValueError):
            return None

        if session.status not in ACTIVE_STATUSES:
            return None

        if session.user_id == self.user.id:
            return 'owner', None

        if not are_friends(self.user.id, session.user_id):
            return None, None

        snapshot = None
        if session.is_location_shared:
            last = get_last_path(session)
            if last:
                snapshot = {
                    'user_id': session.user_id,
                    'walk_id': session.id,
                    'latitude': float(last.latitude),
                    'longitude': float(last.longitude),
                }
        return 'friend', snapshot

    @database_sync_to_async
    def load_owner_context(self):
        session = WalkingSession.objects.select_related('user', 'pet').get(id=self.walk_id)
        groups = [user_group(fid) for fid in get_friend_ids(self.user.id)]
        return groups, get_walker_profile(session)

    @database_sync_to_async
    def process_location(self, data):
        items = data if isinstance(data, list) else [data]
        serializer = WalkingPathBatchSerializer(data=items, many=True)
        if not serializer.is_valid():
            return {'error': '좌표 형식이 올바르지 않습니다.', 'detail': serializer.errors}

        with transaction.atomic():
            try:
                session = WalkingSession.objects.select_for_update().get(
                    id=self.walk_id, user_id=self.user.id
                )
            except WalkingSession.DoesNotExist:
                return {'error': '산책 세션을 찾을 수 없습니다.'}

            if session.status != 'WALKING':
                return {'error': '일시정지 또는 종료 상태에서는 위치를 기록할 수 없습니다.'}

            created = append_locations(session, serializer.validated_data)
            latest = created[-1] if created else None

            return {
                'is_location_shared': session.is_location_shared,
                'latest': (float(latest.latitude), float(latest.longitude)) if latest else None,
            }


# ═════════════════════════════════════════════
# 근처 친구 목록: ws/nearby/?token=...
# ═════════════════════════════════════════════
class NearbyFriendsConsumer(AsyncWebsocketConsumer):
    """
    - my_location: DB에서 위치 공유 중인 친구를 다시 불러와 목록 전송
    - set_radius: 반경 변경 + 사용자 설정에 저장 (다음 접속에도 유지)
    - friend_location / friend_hidden: 메모리에서만 갱신해 즉시 재전송
    """

    async def connect(self):
        self.user = self.scope.get('user', None)
        self.joined = False

        if not self.user or not getattr(self.user, 'is_authenticated', False):
            await self.close(code=CLOSE_UNAUTHENTICATED)
            return

        # 반경 우선순위: URL ?radius= (이번 연결만) > 저장된 설정 > 기본값 5km
        saved_radius = await self.load_saved_radius()
        query = parse_qs(self.scope.get('query_string', b'').decode('utf-8'))
        self.radius_km = _parse_radius(query.get('radius', [None])[0], saved_radius)

        self.my_coords = None      # 내 위치는 클라이언트가 my_location으로 보내줘야 앎
        self.friends = {}          # user_id → 위치 공유 중인 친구 정보

        self.group_name = user_group(self.user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        self.joined = True
        await self.accept()

    async def disconnect(self, close_code):
        if self.joined:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or '')
        except json.JSONDecodeError:
            await _send_error(self, "JSON 형식이 아닙니다.")
            return

        msg_type = data.get('type') if isinstance(data, dict) else None

        if msg_type == 'my_location':
            await self.handle_my_location(data)
        elif msg_type == 'set_radius':
            await self.handle_set_radius(data)
        else:
            await _send_error(self, "type은 'my_location' 또는 'set_radius'만 가능합니다.")

    async def handle_my_location(self, data):
        coords = _parse_coords(data)
        if coords is None:
            await _send_error(self, "latitude/longitude 값이 올바르지 않습니다.")
            return

        self.my_coords = coords
        # 매번 DB에서 다시 불러와서, 놓친 이벤트가 있어도 자동 보정
        self.friends = await self.load_active_friends()
        await self.send_nearby()

    async def handle_set_radius(self, data):
        radius = _parse_radius(data.get('radius'), None)
        if radius is None:
            await _send_error(self, f"radius는 0보다 큰 숫자여야 합니다. (최대 {MAX_RADIUS_KM:g}km)")
            return

        self.radius_km = radius
        await self.save_radius(radius)

        await self.send(text_data=json.dumps({
            'type': 'radius_updated',
            'radius_km': radius,
        }))
        # 위치를 이미 알고 있으면 바뀐 반경으로 목록 즉시 재전송 (메모리 계산, DB 조회 없음)
        if self.my_coords:
            await self.send_nearby()

    # ── 그룹 이벤트 핸들러 ──────────────────────────
    async def friend_location(self, event):
        self.friends[event['user_id']] = {
            key: event.get(key)
            for key in ('user_id', 'walk_id', 'nickname', 'pet_name', 'latitude', 'longitude')
        }
        if self.my_coords:
            await self.send_nearby()

    async def friend_hidden(self, event):
        removed = self.friends.pop(event['user_id'], None)
        if removed is not None and self.my_coords:
            await self.send_nearby()

    # ── 목록 계산/전송 ─────────────────────────────
    async def send_nearby(self):
        nearby = []
        for friend in self.friends.values():
            distance = geodesic(self.my_coords, (friend['latitude'], friend['longitude'])).km
            if distance <= self.radius_km:
                nearby.append({**friend, 'distance_km': round(distance, 2)})
        nearby.sort(key=lambda f: f['distance_km'])

        await self.send(text_data=json.dumps({
            'type': 'nearby_friends',
            'radius_km': self.radius_km,
            'friends': nearby,
        }, ensure_ascii=False))

    # ── DB ───────────────────────────────────────
    @database_sync_to_async
    def load_saved_radius(self):
        pref = WalkPreference.objects.filter(user=self.user).only('nearby_radius_km').first()
        return pref.nearby_radius_km if pref else DEFAULT_RADIUS_KM

    @database_sync_to_async
    def save_radius(self, radius):
        WalkPreference.objects.update_or_create(
            user=self.user,
            defaults={'nearby_radius_km': radius},
        )

    @database_sync_to_async
    def load_active_friends(self):
        friend_ids = get_friend_ids(self.user.id)
        if not friend_ids:
            return {}

        sessions = WalkingSession.objects.filter(
            user_id__in=friend_ids,
            status__in=ACTIVE_STATUSES,
            is_location_shared=True,
        ).select_related('user', 'pet')

        friends = {}
        for session in sessions:
            last = get_last_path(session)
            if not last:
                continue
            friends[session.user_id] = {
                'user_id': session.user_id,
                'walk_id': session.id,
                **get_walker_profile(session),
                'latitude': float(last.latitude),
                'longitude': float(last.longitude),
            }
        return friends

import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import transaction
from django.db.models import Q

from friends.models import Friend
from .models import WalkingSession
from .serializers import WalkingPathBatchSerializer
from .services import append_locations, get_last_path
from .realtime import walk_group

ACTIVE_STATUSES = ('WALKING', 'PAUSED')

# 종료 코드
CLOSE_UNAUTHENTICATED = 4001
CLOSE_FORBIDDEN = 4003
CLOSE_NOT_FOUND = 4004   # 없는 세션 또는 이미 종료된 산책


def are_friends(user_id, other_user_id):
    """수락된 친구 관계인지 (요청 방향 무관)"""
    return Friend.objects.filter(status=Friend.Status.ACCEPTED).filter(
        Q(requester_id=user_id, receiver_id=other_user_id)
        | Q(requester_id=other_user_id, receiver_id=user_id)
    ).exists()


class WalkConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.walk_id = self.scope['url_route']['kwargs']['walk_id']
        self.room_group_name = walk_group(self.walk_id)
        self.user = self.scope.get('user', None)
        self.role = None       # 'owner' | 'friend'
        self.joined = False

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
        # 좌표 전송은 산책 주인만 가능
        if self.role != 'owner' or text_data is None:
            return

        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return

        result = await self.process_location(data)
        if not result:
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
    def process_location(self, data):
        items = data if isinstance(data, list) else [data]
        serializer = WalkingPathBatchSerializer(data=items, many=True)
        if not serializer.is_valid():
            return None

        with transaction.atomic():
            try:
                session = WalkingSession.objects.select_for_update().get(
                    id=self.walk_id, user_id=self.user.id
                )
            except WalkingSession.DoesNotExist:
                return None

            if session.status != 'WALKING':
                return None

            created = append_locations(session, serializer.validated_data)
            latest = created[-1] if created else None

            return {
                'is_location_shared': session.is_location_shared,
                'latest': (float(latest.latitude), float(latest.longitude)) if latest else None,
            }

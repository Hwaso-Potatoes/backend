import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import WalkingSession, WalkingPath


class WalkConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.walk_id = self.scope['url_route']['kwargs']['walk_id']
        self.room_group_name = f'walk_{self.walk_id}'
        self.user = self.scope.get('user', None)

        if not self.user or not getattr(self.user, 'is_authenticated', False):
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            latitude = data.get('latitude')
            longitude = data.get('longitude')

            if latitude is not None and longitude is not None:
                # DB 저장 결과와 위치 공유 가능 여부를 각각 따로 전달받음
                is_saved, is_location_shared = await self.process_location(latitude, longitude)

                # 위치 공유(is_location_shared)가 켜져 있고 산책 중일 때만 다른 사람들에게 전달
                if is_location_shared:
                    user_id = self.user.id if (self.user and getattr(self.user, 'is_authenticated', False)) else None
                    
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'walk_location',
                            'latitude': latitude,
                            'longitude': longitude,
                            'user_id': user_id
                        }
                    )
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    async def walk_location(self, event):
        await self.send(text_data=json.dumps({
            'latitude': event['latitude'],
            'longitude': event['longitude'],
            'user_id': event['user_id']
        }))

    @database_sync_to_async
    def process_location(self, latitude, longitude):
        
        try:
            session = WalkingSession.objects.get(id=self.walk_id)

            # 일시정지(PAUSED)나 종료(FINISHED) 상태면 아무 작업도 하지 않음
            if session.status != 'WALKING':
                return False, False

            # 1. DB 경로 저장 (WALKING 상태이면 무조건 저장)
            WalkingPath.objects.create(
                session=session,
                latitude=float(latitude),
                longitude=float(longitude)
            )

            # 2. 실시간 위치 공유 여부 결정 (WALKING 이면서 + is_location_shared가 True일 때만)
            can_share_location = session.is_location_shared

            return True, can_share_location

        except (WalkingSession.DoesNotExist, ValueError, TypeError):
            return False, False
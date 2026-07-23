import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import WalkingSession, WalkingPath


class WalkConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.walk_id = self.scope['url_route']['kwargs']['walk_id']
        self.room_group_name = f'walk_{self.walk_id}'
        self.user = self.scope.get('user', None)

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

            # 좌표 데이터가 존재하는 경우에만 처리
            if latitude is not None and longitude is not None:
                # 1. DB에 위치 저장 (상태 조건 만족 시에만 저장됨)
                is_saved = await self.save_location(latitude, longitude)

                # 2. 실시간 좌표 브로드캐스트 (DB에 정상적으로 저장/인정된 경우에만 전송)
                if is_saved:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'walk_location',
                            'latitude': latitude,
                            'longitude': longitude,
                            'user_id': self.user.id if self.user and self.user.is_authenticated else None
                        }
                    )
        except json.JSONDecodeError:
            pass

    async def walk_location(self, event):
        await self.send(text_data=json.dumps({
            'latitude': event['latitude'],
            'longitude': event['longitude'],
            'user_id': event['user_id']
        }))

    @database_sync_to_async
    def save_location(self, latitude, longitude):
        try:
            session = WalkingSession.objects.get(id=self.walk_id)

            # 1) 산책 중(WALKING) 상태일 때만
            # 2) 위치 공유(is_location_shared)가 켜져 있을 때만 DB 저장
            if session.status == 'WALKING' and session.is_location_shared:
                WalkingPath.objects.create(
                    session=session,
                    latitude=latitude,
                    longitude=longitude
                )
                return True
        except WalkingSession.DoesNotExist:
            pass
        return False
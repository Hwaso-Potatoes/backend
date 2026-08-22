import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from django.contrib.auth import get_user_model
from .models import WalkingSession, WalkingPath

User = get_user_model()


class WalkConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.walk_id = self.scope['url_route']['kwargs']['walk_id']
        self.room_group_name = f'walk_{self.walk_id}'

        # JWTAuthMiddleware에서 인증된 scope 유저 사용
        self.user = self.scope.get('user', None)

        # 미인증 상태면 연결 거부
        if not self.user or not getattr(self.user, 'is_authenticated', False):
            await self.close(code=4001)
            return

        await self.accept()

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

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
                is_saved, is_location_shared = await self.process_location(latitude, longitude)

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

            if session.status != 'WALKING':
                return False, False

            WalkingPath.objects.create(
                session=session,
                latitude=float(latitude),
                longitude=float(longitude)
            )

            can_share_location = session.is_location_shared

            return True, can_share_location

        except (WalkingSession.DoesNotExist, ValueError, TypeError):
            return False, False
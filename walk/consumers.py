import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import WalkingSession, LocationPoint

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
        data = json.loads(text_data)
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if latitude and longitude:
            await self.save_location(latitude, longitude)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'walk_location',
                'latitude': latitude,
                'longitude': longitude,
                'user_id': self.user.id if self.user and self.user.is_authenticated else None
            }
        )

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
            LocationPoint.objects.create(
                session=session,
                latitude=latitude,
                longitude=longitude
            )
        except WalkingSession.DoesNotExist:
            pass
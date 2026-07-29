from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/walks/(?P<walk_id>\d+)/$', consumers.WalkConsumer.as_asgi()),
]
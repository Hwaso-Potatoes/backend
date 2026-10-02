import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

logger = logging.getLogger(__name__)


def walk_group(walk_id):
    return f"walk_{walk_id}"


def _send(walk_id, payload):
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(walk_group(walk_id), payload)
    except Exception:
        # 브로드캐스트 실패가 API 실패로 번지지 않도록
        logger.exception("산책 브로드캐스트 실패 (walk_id=%s)", walk_id)


def broadcast_location(session, latitude, longitude):
    """동기 코드(REST)에서 호출. DB 커밋 후 전송."""
    walk_id = session.id
    payload = {
        "type": "walk_location",           # WalkConsumer.walk_location()
        "user_id": session.user_id,
        "walk_id": walk_id,
        "latitude": float(latitude),
        "longitude": float(longitude),
    }
    transaction.on_commit(lambda: _send(walk_id, payload))


def broadcast_location_hidden(session, reason):
    """친구 지도에서 마커 제거 요청. reason: 'sharing_off' | 'walk_ended'"""
    walk_id = session.id
    payload = {
        "type": "walk_location_hidden",    # WalkConsumer.walk_location_hidden()
        "user_id": session.user_id,
        "walk_id": walk_id,
        "reason": reason,
    }
    transaction.on_commit(lambda: _send(walk_id, payload))

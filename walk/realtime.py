import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from .services import get_friend_ids, get_walker_profile

logger = logging.getLogger(__name__)


def walk_group(walk_id):
    """산책 세션별 방 (그 산책을 보는 사람들)"""
    return f"walk_{walk_id}"


def user_group(user_id):
    """사용자별 개인 채널 (근처 친구 목록용)"""
    return f"user_{user_id}"


def _send_groups(groups, payload):
    layer = get_channel_layer()
    if layer is None:
        return
    for group in groups:
        try:
            async_to_sync(layer.group_send)(group, payload)
        except Exception:
            # 브로드캐스트 실패가 API 실패로 번지지 않도록
            logger.exception("브로드캐스트 실패 (group=%s)", group)


def broadcast_location(session, latitude, longitude):
    """동기 코드(REST)에서 호출. DB 커밋 후 산책방 + 친구들 개인 채널로 전송."""
    lat, lng = float(latitude), float(longitude)
    walk_id = session.id

    walk_payload = {
        "type": "walk_location",           # WalkConsumer.walk_location()
        "user_id": session.user_id,
        "walk_id": walk_id,
        "latitude": lat,
        "longitude": lng,
    }
    friend_payload = {
        "type": "friend_location",         # NearbyFriendsConsumer.friend_location()
        "user_id": session.user_id,
        "walk_id": walk_id,
        **get_walker_profile(session),
        "latitude": lat,
        "longitude": lng,
    }
    friend_groups = [user_group(fid) for fid in get_friend_ids(session.user_id)]

    def _run():
        _send_groups([walk_group(walk_id)], walk_payload)
        _send_groups(friend_groups, friend_payload)

    transaction.on_commit(_run)


def broadcast_location_hidden(session, reason):
    """친구 지도/목록에서 제거 요청. reason: 'sharing_off' | 'walk_ended'"""
    walk_id = session.id

    walk_payload = {
        "type": "walk_location_hidden",    # WalkConsumer.walk_location_hidden()
        "user_id": session.user_id,
        "walk_id": walk_id,
        "reason": reason,
    }
    friend_payload = {
        "type": "friend_hidden",           # NearbyFriendsConsumer.friend_hidden()
        "user_id": session.user_id,
        "walk_id": walk_id,
        "reason": reason,
    }
    friend_groups = [user_group(fid) for fid in get_friend_ids(session.user_id)]

    def _run():
        _send_groups([walk_group(walk_id)], walk_payload)
        _send_groups(friend_groups, friend_payload)

    transaction.on_commit(_run)

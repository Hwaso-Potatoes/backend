import hashlib
import secrets

import redis
from django.conf import settings


FRIEND_QR_TTL_SECONDS = 300


class FriendQRTokenError(Exception):
    pass


def _get_redis_client():
    return redis.Redis.from_url(
        settings.AUTH_REDIS_URL,
        decode_responses=True,
    )


def _build_friend_qr_key(token):
    token_hash = hashlib.sha256(
        token.encode()
    ).hexdigest()

    return f"friend:qr:{token_hash}"


# 토큰 생성
def generate_friend_qr_token(user_id):
    redis_client = _get_redis_client()

    token = secrets.token_urlsafe(32)

    redis_client.set(
        _build_friend_qr_key(token),
        user_id,
        ex=FRIEND_QR_TTL_SECONDS,
    )

    return token


# 토큰 유효성 확인 및 소유자 확인
def get_friend_qr_owner_id(token):
    redis_client = _get_redis_client()

    user_id = redis_client.get(
        _build_friend_qr_key(token)
    )

    if not user_id:
        raise FriendQRTokenError(
            "QR 코드가 만료되었거나 유효하지 않습니다."
        )

    return int(user_id)


# 친구 추가 직전에 토큰을 한 번만 사용하고 삭제
def consume_friend_qr_token(token):
    redis_client = _get_redis_client()

    user_id = redis_client.getdel(
        _build_friend_qr_key(token)
    )

    if not user_id:
        raise FriendQRTokenError(
            "QR 코드가 이미 사용되었거나 만료되었습니다."
        )

    return int(user_id)
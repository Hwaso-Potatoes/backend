import hashlib
import secrets

import redis
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password


CODE_TTL_SECONDS = 300
RESEND_COOLDOWN_SECONDS = 60
MAX_ATTEMPTS = 5
VERIFICATION_TOKEN_TTL_SECONDS = 600


class SignupCodeCooldownError(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after


class SignupCodeVerificationError(Exception):
    pass


def get_auth_redis():
    return redis.Redis.from_url(
        settings.AUTH_REDIS_URL,
        decode_responses=True,
    )


def issue_signup_code(email):
    email = email.lower().strip()

    redis_client = get_auth_redis()

    code_key = f"signup:code:{email}"
    cooldown_key = f"signup:cooldown:{email}"

    if redis_client.exists(cooldown_key):
        retry_after = redis_client.ttl(cooldown_key)

        raise SignupCodeCooldownError(
            retry_after,
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    code_hash = make_password(code)

    redis_client.hset(
        code_key,
        mapping={
            "code_hash": code_hash,
            "attempt_count": 0,
        },
    )

    redis_client.expire(
        code_key,
        CODE_TTL_SECONDS,
    )

    redis_client.set(
        cooldown_key,
        "1",
        ex=RESEND_COOLDOWN_SECONDS,
    )

    return code


def clear_signup_code(email):
    email = email.lower().strip()

    redis_client = get_auth_redis()

    redis_client.delete(
        f"signup:code:{email}",
        f"signup:cooldown:{email}",
    )


def verify_signup_code(email, code):
    email = email.lower().strip()

    redis_client = get_auth_redis()

    code_key = f"signup:code:{email}"

    verification_data = redis_client.hgetall(
        code_key,
    )

    if not verification_data:
        raise SignupCodeVerificationError("인증번호가 만료되었거나 존재하지 않습니다.")

    attempt_count = int(
        verification_data.get(
            "attempt_count",
            0,
        )
    )

    if attempt_count >= MAX_ATTEMPTS:
        redis_client.delete(code_key)

        raise SignupCodeVerificationError("인증 시도 횟수를 초과했습니다.")

    code_hash = verification_data["code_hash"]

    if not check_password(
        code,
        code_hash,
    ):
        attempt_count = redis_client.hincrby(
            code_key,
            "attempt_count",
            1,
        )

        if attempt_count >= MAX_ATTEMPTS:
            redis_client.delete(code_key)

        raise SignupCodeVerificationError("인증번호가 일치하지 않습니다.")

    redis_client.delete(code_key)

    verification_token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        verification_token.encode()
    ).hexdigest()

    verified_key = f"signup:verified:{token_hash}"

    redis_client.set(
        verified_key,
        email,
        ex=VERIFICATION_TOKEN_TTL_SECONDS,
    )

    return verification_token

class SignupVerificationTokenError(Exception):
    pass


def validate_signup_verification_token(email, verification_token):
    email = email.lower().strip()

    redis_client = get_auth_redis()

    token_hash = hashlib.sha256(
        verification_token.encode()
    ).hexdigest()

    verified_key = f"signup:verified:{token_hash}"

    verified_email = redis_client.get(verified_key)

    if not verified_email:
        raise SignupVerificationTokenError("이메일 인증이 만료되었거나 유효하지 않습니다.")

    if verified_email != email:
        raise SignupVerificationTokenError("인증한 이메일과 회원가입 이메일이 일치하지 않습니다.")


def delete_signup_verification_token(verification_token):
    redis_client = get_auth_redis()

    token_hash = hashlib.sha256(
        verification_token.encode()
    ).hexdigest()

    redis_client.delete(
        f"signup:verified:{token_hash}"
    )
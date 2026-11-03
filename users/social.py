import requests
import jwt
from jwt import PyJWKClient
from django.conf import settings


def get_kakao_user(access_token):
    resp = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {access_token}"}, timeout=5,
    )
    resp.raise_for_status()
    data = resp.json()
    account = data.get("kakao_account", {})
    return {"id": str(data.get("id")),
            "email": account.get("email"),
            "nickname": account.get("profile", {}).get("nickname", "")}


def get_google_user(access_token):
    resp = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}, timeout=5,
    )
    resp.raise_for_status()
    data = resp.json()
    return {"id": str(data.get("sub")),
            "email": data.get("email"),
            "nickname": data.get("name", "")}


def get_apple_user(identity_token):
    jwks_client = PyJWKClient("https://appleid.apple.com/auth/keys")
    signing_key = jwks_client.get_signing_key_from_jwt(identity_token)
    decoded = jwt.decode(
        identity_token, signing_key.key, algorithms=["RS256"],
        audience=settings.APPLE_CLIENT_ID,      
        issuer="https://appleid.apple.com",
    )
    return {"id": decoded.get("sub"),
            "email": decoded.get("email"),
            "nickname": ""}


PROVIDERS = {
    "kakao":  ("access_token", get_kakao_user),
    "google": ("access_token", get_google_user),
    "apple":  ("identity_token", get_apple_user),
}
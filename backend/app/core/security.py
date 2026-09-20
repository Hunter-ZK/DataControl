from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

AUTH_SECRET = os.getenv("DATACONTROL_AUTH_SECRET", "datacontrol-dev-secret-change-me").encode()
TOKEN_TTL_SECONDS = int(os.getenv("DATACONTROL_TOKEN_TTL_SECONDS", "28800"))


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded or "$" not in encoded:
        return False
    salt_text, digest_text = encoded.split("$", 1)
    try:
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
    except ValueError:
        return False
    actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return hmac.compare_digest(actual, expected)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "uid": user_id,
        "sub": username,
        "role": role,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64(hmac.new(AUTH_SECRET, body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


@dataclass(frozen=True)
class TokenPayload:
    user_id: int
    username: str
    role: str


def decode_token(token: str) -> TokenPayload | None:
    try:
        body, signature = token.split(".", 1)
        expected = _b64(hmac.new(AUTH_SECRET, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_unb64(body))
        if int(payload["exp"]) < int(time.time()):
            return None
        return TokenPayload(int(payload["uid"]), str(payload["sub"]), str(payload["role"]))
    except (ValueError, KeyError, json.JSONDecodeError):
        return None

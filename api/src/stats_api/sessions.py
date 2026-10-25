"""Signed tokens: the app's session token, and the OAuth `state` that carries the app's return
address through Spotify's login.

A token is `<payload>.<signature>`: base64url JSON, then base64url HMAC-SHA256 of it. Anyone
can read a payload, so it never holds secrets; only the server can make a valid signature.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

SESSION_TTL_S = 30 * 24 * 3600
STATE_TTL_S = 10 * 60


class InvalidToken(Exception):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _signature(secret: str, payload: str, purpose: str) -> str:
    message = f"{purpose}.{payload}".encode()
    return _b64(hmac.new(secret.encode(), message, hashlib.sha256).digest())


def sign(
    secret: str, claims: dict[str, Any], purpose: str, ttl_s: int, now: float | None = None
) -> str:
    """`purpose` stops a token made for one use (say, OAuth state) being accepted for another."""
    issued = time.time() if now is None else now
    payload = _b64(json.dumps({**claims, "exp": int(issued + ttl_s)}).encode())
    return f"{payload}.{_signature(secret, payload, purpose)}"


def verify(secret: str, token: str, purpose: str, now: float | None = None) -> dict[str, Any]:
    payload, _, signature = token.partition(".")
    if not signature or not hmac.compare_digest(signature, _signature(secret, payload, purpose)):
        raise InvalidToken("bad signature")
    try:
        claims = json.loads(_unb64(payload))
    except ValueError as e:
        raise InvalidToken("unreadable payload") from e
    if claims.get("exp", 0) < (time.time() if now is None else now):
        raise InvalidToken("expired")
    return claims

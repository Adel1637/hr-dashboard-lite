"""Jetons d'accès JWT signés (HS256) avec expiration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

ALGORITHM = "HS256"


class TokenError(Exception):
    pass


def create_token(username: str, role: str, version: int, secret: str,
                 minutes: int) -> tuple[str, int]:
    now = datetime.now(UTC)
    payload = {
        "sub": username,
        "role": role,
        "ver": version,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM), minutes * 60


def decode_token(token: str, secret: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM],
                          options={"require": ["sub", "exp", "iat"]})
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("invalid") from exc

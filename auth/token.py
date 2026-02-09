"""
Helpers for creating and validating signed auth tokens.

These tokens are used to keep users logged in across browser refreshes.
They are passed via URL query parameters (not cookies).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from config import get_auth_token_secret, get_auth_token_ttl_minutes


def create_session_token(user_id: int, company_id: int, email: str) -> str:
    """Create a signed JWT for the given user and company."""
    secret = get_auth_token_secret()
    ttl_minutes = get_auth_token_ttl_minutes()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "uid": user_id,
        "cid": company_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    # PyJWT may return str or bytes depending on version
    return token.decode("utf-8") if isinstance(token, bytes) else token


def decode_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a session token, or return None if invalid/expired."""
    secret = get_auth_token_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        return None


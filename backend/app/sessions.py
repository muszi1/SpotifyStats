import secrets
import time
from typing import Dict, Optional, TypedDict

from fastapi import Request
from .config import IS_PROD

SESSION_COOKIE_NAME = "spotify_session_id"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 6  # 6 hours

class SessionData(TypedDict, total=False):
    access_token: str
    refresh_token: str | None
    expires_at: float | None

_SESSIONS: Dict[str, SessionData] = {}

def new_session_id() -> str:
    return secrets.token_urlsafe(32)

def get_session(session_id: str | None) -> Optional[SessionData]:
    if not session_id:
        return None
    return _SESSIONS.get(session_id)

def save_tokens(session_id: str, token_data: dict) -> SessionData:
    expires_in = token_data.get("expires_in")
    expires_at = time.time() + int(expires_in) if expires_in else None
    session: SessionData = {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "expires_at": expires_at,
    }
    _SESSIONS[session_id] = session
    return session

def session_cookie_kwargs(request: Request | None = None) -> dict:
    secure = IS_PROD
    if request and request.url.scheme == "https":
        secure = True
    return {
        "max_age": SESSION_COOKIE_MAX_AGE,
        "httponly": True,
        "secure": secure,
        "samesite": "lax",
    }

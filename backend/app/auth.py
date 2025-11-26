import base64
import json
import secrets
import urllib.parse
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from .config import (
    IS_PROD,
    SPOTIFY_AUTH_URL,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPES,
    FRONTEND_BASE_URL,
    require_config,
)
from .sessions import (
    SESSION_COOKIE_NAME,
    session_cookie_kwargs,
    get_session,
    new_session_id,
    save_tokens,
)
from .spotify_api import exchange_code_for_token, SpotifyAPIError

router = APIRouter(prefix="/auth", tags=["auth"])

STATE_COOKIE_NAME = "spotify_auth_state"
STATE_COOKIE_MAX_AGE = 600  # seconds

def _encode_state() -> str:
    payload = {"nonce": secrets.token_urlsafe(16)}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")

def _decode_state(state: str) -> dict:
    try:
        raw = base64.urlsafe_b64decode(state.encode("utf-8"))
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid state payload") from exc

@router.get("/login")
def login(force_login: bool = False):
    try:
        require_config()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    scope = " ".join(SPOTIFY_SCOPES)
    state = _encode_state()
    params = {
        "response_type": "code",
        "client_id": SPOTIFY_CLIENT_ID,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": scope,
        "state": state,
    }
    if force_login:
        params["show_dialog"] = "true"
    url = f"{SPOTIFY_AUTH_URL}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"
    response = RedirectResponse(url)
    response.set_cookie(
        STATE_COOKIE_NAME,
        state,
        max_age=STATE_COOKIE_MAX_AGE,
        httponly=True,
        secure=IS_PROD,
        samesite="lax",
    )
    return response

@router.get("/callback")
def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify authorization failed: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    expected_state = request.cookies.get(STATE_COOKIE_NAME)
    if not expected_state or state != expected_state:
        raise HTTPException(status_code=400, detail="State mismatch; possible CSRF attempt")

    _decode_state(state)  # validates payload

    try:
        token_data = exchange_code_for_token(code=code, redirect_uri=SPOTIFY_REDIRECT_URI)
    except SpotifyAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    session_id = request.cookies.get(SESSION_COOKIE_NAME) or new_session_id()
    save_tokens(session_id, token_data)

    redirect_target = FRONTEND_BASE_URL.rstrip("/") or "/"
    if not redirect_target.startswith("http"):
        # relative path, keep on same host
        redirect_target = redirect_target if redirect_target.startswith("/") else f"/{redirect_target}"
    redirect_url = f"{redirect_target}?login=success"

    response = RedirectResponse(url=redirect_url)
    response.delete_cookie(STATE_COOKIE_NAME)
    response.set_cookie(SESSION_COOKIE_NAME, session_id, **session_cookie_kwargs(request))
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie(SESSION_COOKIE_NAME)
    response.delete_cookie(STATE_COOKIE_NAME)
    return response

import base64
import json
import secrets
import urllib.parse
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from .config import (
    SPOTIFY_AUTH_URL,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPES,
)
from .spotify_api import exchange_code_for_token, get_top_tracks, SpotifyAPIError

router = APIRouter(prefix="/auth", tags=["auth"])

STATE_COOKIE_NAME = "spotify_auth_state"
STATE_COOKIE_MAX_AGE = 600  # seconds


def _encode_state(forward_to: str | None = None) -> str:
    payload = {"nonce": secrets.token_urlsafe(16), "forward_to": forward_to}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _decode_state(state: str) -> dict:
    try:
        raw = base64.urlsafe_b64decode(state.encode("utf-8"))
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid state payload") from exc


@router.get("/login")
def login(redirect_uri: str | None = None, forward_to: str | None = None):
    if not SPOTIFY_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Spotify client ID not configured")

    # Always use the configured redirect for Spotify (must match dashboard). We tunnel the
    # frontend redirect target through the state payload so we can bounce the user back.
    target_redirect = SPOTIFY_REDIRECT_URI if not redirect_uri else redirect_uri
    scope = " ".join(SPOTIFY_SCOPES)
    state = _encode_state(forward_to=forward_to)
    params = {
        "response_type": "code",
        "client_id": SPOTIFY_CLIENT_ID,
        "redirect_uri": target_redirect,
        "scope": scope,
        "state": state,
    }
    url = f"{SPOTIFY_AUTH_URL}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"
    response = RedirectResponse(url)
    response.set_cookie(
        STATE_COOKIE_NAME,
        state,
        max_age=STATE_COOKIE_MAX_AGE,
        httponly=True,
        secure=False,
        samesite="lax",
    )
    return response


@router.get("/callback")
def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    redirect_uri: str | None = None,
    exchange_only: bool | None = False,
):
    if error:
        raise HTTPException(status_code=400, detail=f"Spotify authorization failed: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    expected_state = request.cookies.get(STATE_COOKIE_NAME)
    if not expected_state or state != expected_state:
        raise HTTPException(status_code=400, detail="State mismatch; possible CSRF attempt")

    payload = _decode_state(state)
    forward_to = payload.get("forward_to")

    # When called by Spotify (no exchange_only), bounce back to the frontend with the code/state
    # so the SPA can finish the token exchange via XHR and keep the user on the app.
    if not exchange_only and forward_to:
        target = urllib.parse.urlsplit(forward_to)
        query = urllib.parse.parse_qs(target.query)
        query["code"] = [code]
        query["state"] = [state]
        new_query = urllib.parse.urlencode(query, doseq=True)
        redirect_target = urllib.parse.urlunsplit((target.scheme, target.netloc, target.path, new_query, ""))
        response = RedirectResponse(redirect_target)
        return response

    try:
        token_data = exchange_code_for_token(code=code, redirect_uri=redirect_uri or SPOTIFY_REDIRECT_URI)
    except SpotifyAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    response = JSONResponse(token_data)
    response.delete_cookie(STATE_COOKIE_NAME)
    return response


@router.get("/top-tracks")
def top_tracks(access_token: str, limit: int = 20, time_range: str = "medium_term"):
    try:
        items = get_top_tracks(access_token=access_token, limit=limit, time_range=time_range)
    except SpotifyAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return {"items": items}

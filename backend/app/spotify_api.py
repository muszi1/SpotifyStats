from typing import Any, Dict, List
import httpx
from .config import (
    SPOTIFY_API_BASE_URL,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_TOKEN_URL,
)

class SpotifyAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)

def _require_credentials() -> None:
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise SpotifyAPIError(status_code=500, message="Spotify credentials are not configured")

def exchange_code_for_token(*, code: str, redirect_uri: str) -> Dict[str, Any]:
    _require_credentials()

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = httpx.post(
            SPOTIFY_TOKEN_URL,
            data=data,
            headers=headers,
            auth=httpx.BasicAuth(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
            timeout=10,
        )
    except httpx.RequestError as exc:
        raise SpotifyAPIError(status_code=502, message=f"Spotify token endpoint unreachable: {exc}") from exc

    if response.status_code != 200:
        detail = _error_detail(response)
        raise SpotifyAPIError(status_code=response.status_code, message=f"Token exchange failed: {detail}")

    return response.json()

def refresh_access_token(*, refresh_token: str) -> Dict[str, Any]:
    _require_credentials()
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = httpx.post(
            SPOTIFY_TOKEN_URL,
            data=data,
            headers=headers,
            auth=httpx.BasicAuth(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
            timeout=10,
        )
    except httpx.RequestError as exc:
        raise SpotifyAPIError(status_code=502, message=f"Spotify token endpoint unreachable: {exc}") from exc

    if response.status_code != 200:
        detail = _error_detail(response)
        raise SpotifyAPIError(status_code=response.status_code, message=f"Token refresh failed: {detail}")

    payload = response.json()
    if "refresh_token" not in payload:
        payload["refresh_token"] = refresh_token
    return payload

def get_top_tracks(*, access_token: str, limit: int = 20, time_range: str = "medium_term") -> List[Dict[str, Any]]:
    if not access_token:
        raise SpotifyAPIError(status_code=401, message="Access token is required")

    limit = max(1, min(limit, 50))
    params = {"limit": limit, "time_range": time_range}
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = httpx.get(
            f"{SPOTIFY_API_BASE_URL}/me/top/tracks",
            params=params,
            headers=headers,
            timeout=10,
        )
    except httpx.RequestError as exc:
        raise SpotifyAPIError(status_code=502, message=f"Spotify API unreachable: {exc}") from exc

    if response.status_code != 200:
        detail = _error_detail(response)
        raise SpotifyAPIError(status_code=response.status_code, message=f"Failed to fetch top tracks: {detail}")

    data = response.json()
    items = []
    for item in data.get("items", []):
        track_name = item.get("name")
        artists = [artist.get("name") for artist in item.get("artists", []) if artist.get("name")]
        url = item.get("external_urls", {}).get("spotify")
        images = item.get("album", {}).get("images") or []
        image = images[0]["url"] if images else None
        items.append({"name": track_name, "artists": artists, "url": url, "image": image})
    return items

def _error_detail(response: httpx.Response) -> str:
    if response.headers.get("content-type", "").startswith("application/json"):
        body = response.json()
        return (
            body.get("error_description")
            or body.get("error", {}).get("message")
            or str(body)
        )
    return response.text

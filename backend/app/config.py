import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

APP_ENV = os.getenv("APP_ENV", "local").lower()
IS_PROD = APP_ENV == "prod"

def _get_env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)

SPOTIFY_CLIENT_ID = _get_env("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = _get_env("SPOTIFY_CLIENT_SECRET")

if APP_ENV == "local":
    default_redirect = "http://127.0.0.1:8000/auth/callback"
elif APP_ENV == "prod":
    default_redirect = "https://spotify-stats.hu/auth/callback"
else:
    default_redirect = None

SPOTIFY_REDIRECT_URI = _get_env("SPOTIFY_REDIRECT_URI", default_redirect)
SPOTIFY_SCOPES = ["user-top-read"]

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "/")

def require_config() -> None:
    missing = []
    if not SPOTIFY_CLIENT_ID:
        missing.append("SPOTIFY_CLIENT_ID")
    if not SPOTIFY_CLIENT_SECRET:
        missing.append("SPOTIFY_CLIENT_SECRET")
    if not SPOTIFY_REDIRECT_URI:
        missing.append("SPOTIFY_REDIRECT_URI")
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

# Spotify Stats

Simple Spotify top-tracks viewer with a FastAPI backend and a Vite + React frontend. Users sign in with Spotify, the backend completes the OAuth exchange, and the SPA fetches and displays their current top tracks.

## Features
- FastAPI backend for Spotify OAuth (auth redirect, code exchange, top-tracks endpoint)
- React SPA that drives the login flow and displays ranked tracks
- Environment-based configuration for both backend and frontend

## Stack
- Backend: FastAPI, httpx, python-dotenv, uvicorn
- Frontend: Vite, React 18

## Setup

### 1) Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

Backend env (`backend/.env`):
```
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/auth/callback  # must match Spotify app settings
```

Run the API:
```bash
uvicorn app.main:app --reload --port 8000
```

### 2) Frontend
```bash
npm install
npm run dev
```

Frontend env (`frontend/.env`):
```
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/auth/callback
VITE_FRONTEND_REDIRECT_URI=http://127.0.0.1:5173/callback
```

Open the Vite dev server URL (defaults to http://127.0.0.1:5173).

## How the auth flow works
1. SPA links to `${VITE_API_BASE_URL}/auth/login` with redirect/forward params.
2. Backend redirects the user to Spotify with a CSRF-protected state cookie.
3. Spotify calls `/auth/callback`; backend replays the code to Spotify and returns tokens (or forwards the code to the SPA when `exchange_only` is false).
4. SPA stores tokens in localStorage and calls `/auth/top-tracks?access_token=...`.

## Production notes
- Configure CORS/HTTPS as needed for your deployment.
- Keep `.env` files local; `.gitignore` already excludes them.
- Rotate any Spotify credentials if they were ever checked in elsewhere.

## Photo
<img width="2511" height="1397" alt="image" src="https://github.com/user-attachments/assets/d41bcf33-3751-434f-a8b8-6889e86e08d9" />


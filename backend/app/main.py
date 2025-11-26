from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from . import spotify_api
from .auth import router as auth_router
from .sessions import SESSION_COOKIE_NAME, get_session, save_tokens

app = FastAPI()

api_router = APIRouter(prefix="", tags=["api"])

@api_router.get("/me/top-tracks")
def top_tracks(request: Request, limit: int = 20, time_range: str = "medium_term"):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    session = get_session(session_id)
    if not session or not session.get("access_token"):
        raise HTTPException(status_code=401, detail="No active Spotify session. Please log in.")

    try:
        items = spotify_api.get_top_tracks(
            access_token=session["access_token"],
            limit=limit,
            time_range=time_range,
        )
    except spotify_api.SpotifyAPIError as exc:
        if exc.status_code == 401 and session.get("refresh_token"):
            refreshed = spotify_api.refresh_access_token(refresh_token=session["refresh_token"])
            save_tokens(session_id, refreshed)
            items = spotify_api.get_top_tracks(
                access_token=refreshed["access_token"],
                limit=limit,
                time_range=time_range,
            )
        else:
            raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return {"items": items}

app.include_router(auth_router)
app.include_router(api_router)

@app.get("/service")
def health():
    return {"status": "fasza"}

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Spotify Stats</title>
        <style>
          :root { color-scheme: dark; }
          body {
            margin: 0;
            font-family: "Inter", system-ui, -apple-system, sans-serif;
            background: radial-gradient(circle at 20% 20%, #1db95433, transparent 30%), radial-gradient(circle at 80% 0%, #1db95422, transparent 25%), #0d0d0f;
            color: #e6f6ec;
            min-height: 100vh;
          }
          .shell {
            max-width: 960px;
            margin: 0 auto;
            padding: 40px 24px 64px;
          }
          h1 { margin: 0 0 12px; font-size: 32px; letter-spacing: -0.5px; }
          p.lead { margin: 0 0 24px; color: #cde7d7; }
          .actions { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 24px; }
          .btn {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 10px 16px; border-radius: 10px; border: 1px solid #1db95480;
            background: linear-gradient(120deg, #1db954, #11a44a);
            color: #041006; font-weight: 700; text-decoration: none; cursor: pointer;
            box-shadow: 0 10px 30px #1db95433;
          }
          .btn.secondary { background: transparent; color: #dfeee6; border-color: #2f3b33; box-shadow: none; }
          .status { margin: 8px 0 24px; color: #9fcfb6; font-size: 14px; min-height: 18px; }
          .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
          }
          .card {
            background: #121416;
            border: 1px solid #1b1f22;
            border-radius: 12px;
            padding: 14px;
            display: flex;
            gap: 12px;
            align-items: center;
            box-shadow: 0 12px 30px rgba(0,0,0,0.25);
          }
          .cover {
            width: 64px;
            height: 64px;
            border-radius: 8px;
            background: #0f1512;
            object-fit: cover;
            flex-shrink: 0;
          }
          .meta { flex: 1; }
          .title { margin: 0 0 4px; font-weight: 700; font-size: 16px; }
          .artists { margin: 0; color: #b5d7c4; font-size: 14px; }
          .empty { color: #9fb5a9; }
        </style>
      </head>
      <body>
        <div class="shell">
          <h1>Spotify Stats</h1>
          <p class="lead">Jelentkezz be a Spotify-val és nézd meg a top trackjeidet.</p>
          <div class="actions">
            <a class="btn" href="/auth/login">Login with Spotify</a>
            <button class="btn secondary" onclick="loadTracks()">Load My Top Tracks</button>
            <a class="btn secondary" href="/auth/login?force_login=1">Switch Account</a>
            <a class="btn secondary" href="/auth/logout">Logout</a>
          </div>
          <div class="status" id="status"></div>
          <div id="grid" class="grid"></div>
          <p class="empty" id="empty" style="display:none;">Nincs eredmény. Jelentkezz be és töltsd be a top trackjeidet.</p>
        </div>
        <script>
          const params = new URLSearchParams(window.location.search);
          if (params.get("login") === "success") {
            loadTracks();
          }
          async function loadTracks() {
            const status = document.getElementById("status");
            const grid = document.getElementById("grid");
            const empty = document.getElementById("empty");
            status.textContent = "Betöltés...";
            grid.innerHTML = "";
            empty.style.display = "none";
            try {
              const res = await fetch("/me/top-tracks");
              if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                status.textContent = `Hiba ${res.status}: ${err.detail || res.statusText}`;
                return;
              }
              const data = await res.json();
              const items = data.items || [];
              if (!items.length) {
                empty.style.display = "block";
                status.textContent = "";
                return;
              }
              for (const item of items) {
                const card = document.createElement("div");
                card.className = "card";
                const img = document.createElement("img");
                img.className = "cover";
                img.src = item.image || "https://via.placeholder.com/64?text=%20";
                img.alt = item.name || "Cover";
                const meta = document.createElement("div");
                meta.className = "meta";
                const title = document.createElement("div");
                title.className = "title";
                title.textContent = item.name || "Unknown track";
                const artists = document.createElement("div");
                artists.className = "artists";
                artists.textContent = (item.artists || []).join(", ");
                meta.appendChild(title);
                meta.appendChild(artists);
                card.appendChild(img);
                card.appendChild(meta);
                if (item.url) {
                  card.onclick = () => window.open(item.url, "_blank");
                  card.style.cursor = "pointer";
                }
                grid.appendChild(card);
              }
              status.textContent = "";
            } catch (err) {
              status.textContent = "Request failed: " + err;
            }
          }
        </script>
      </body>
    </html>
    """

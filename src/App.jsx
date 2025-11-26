import { useEffect, useMemo, useState } from "react";
import { exchangeCodeForToken, fetchTopTracks, getLoginUrl } from "./api";

const STORAGE_KEY = "spotifyTokens";

export default function App() {
  const [auth, setAuth] = useState(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
  });
  const [tracks, setTracks] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | auth | loading
  const [error, setError] = useState("");

  const spotifyRedirectUri = useMemo(() => {
    const fromEnv = import.meta.env.VITE_SPOTIFY_REDIRECT_URI?.trim();
    return fromEnv || "http://127.0.0.1:8000/auth/callback";
  }, []);

  const frontendCallbackUri = useMemo(() => {
    const fromEnv = import.meta.env.VITE_FRONTEND_REDIRECT_URI?.trim();
    return fromEnv || `${window.location.origin}/callback`;
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");
    if (code && state) {
      completeAuth({ code, state });
    }
    // Clean up URL so we don't retry on refresh
    if (code || state) {
      const url = new URL(window.location.href);
      url.search = "";
      window.history.replaceState({}, "", url.toString());
    }
  }, [spotifyRedirectUri]);

  useEffect(() => {
    if (auth?.access_token) {
      loadTopTracks();
    }
  }, [auth]);

  const completeAuth = async ({ code, state }) => {
    setStatus("auth");
    setError("");
    try {
      const tokens = await exchangeCodeForToken({ code, state, redirectUri: spotifyRedirectUri });
      setAuth(tokens);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
    } catch (err) {
      setError(err.message || "Failed to complete Spotify login");
    } finally {
      setStatus("idle");
    }
  };

  const loadTopTracks = async () => {
    if (!auth?.access_token) return;
    setStatus("loading");
    setError("");
    try {
      const data = await fetchTopTracks({ accessToken: auth.access_token });
      setTracks(data.items || []);
    } catch (err) {
      setError(err.message || "Could not load tracks");
    } finally {
      setStatus("idle");
    }
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setAuth(null);
    setTracks([]);
  };

  const loggedIn = Boolean(auth?.access_token);

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Spotify Stats</p>
          <h1>
            See your top tracks
            <br />
            without leaving the browser
          </h1>
          <p className="lede">
            Authorize with Spotify, then we’ll fetch your favorites through the FastAPI backend.
          </p>
          <div className="actions">
            {loggedIn ? (
              <>
                <button className="primary" onClick={loadTopTracks} disabled={status !== "idle"}>
                  {status === "loading" ? "Refreshing..." : "Refresh tracks"}
                </button>
                <button className="ghost" onClick={logout}>
                  Sign out
                </button>
              </>
            ) : (
              <a
                className="primary"
                href={getLoginUrl({ redirectUri: spotifyRedirectUri, forwardTo: frontendCallbackUri })}
              >
                Log in with Spotify
              </a>
            )}
          </div>
          {!loggedIn && (
            <p className="hint">After authorizing, you’ll land back here automatically.</p>
          )}
        </div>
        <div className="card">
          <p className="label">Status</p>
          <p className="value">
            {status === "auth" && "Connecting to Spotify..."}
            {status === "loading" && "Loading your top tracks..."}
            {status === "idle" && (loggedIn ? "Ready" : "Waiting for login")}
          </p>
          {auth?.access_token && (
            <div className="token">
              <p className="label">Access token</p>
              <p className="mono">{auth.access_token.slice(0, 24)}...</p>
            </div>
          )}
          {error && <p className="error">{error}</p>}
        </div>
      </header>

      <main>
        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="label">Top tracks</p>
              <h2>Your current favorites</h2>
            </div>
            {loggedIn && (
              <button className="ghost" onClick={loadTopTracks} disabled={status !== "idle"}>
                {status === "loading" ? "Refreshing..." : "Refresh"}
              </button>
            )}
          </div>
          {!loggedIn && (
            <p className="hint">Log in with Spotify to load your data.</p>
          )}
          {loggedIn && tracks.length === 0 && status === "idle" && (
            <p className="hint">No tracks yet. Try refreshing after you listen to some music.</p>
          )}
          <div className="tracks">
            {tracks.map((track, idx) => (
              <article key={track.id || idx} className="track">
                <div className="track-rank">#{idx + 1}</div>
                <div className="track-info">
                  <p className="track-title">{track.name}</p>
                  <p className="track-meta">
                    {track.artists?.map((artist) => artist.name).join(", ")} • {track.album?.name}
                  </p>
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

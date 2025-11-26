const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "";

const handleResponse = async (response) => {
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof body === "object" && body?.detail ? body.detail : body;
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return body;
};

export const getLoginUrl = ({ redirectUri, forwardTo } = {}) => {
  const params = new URLSearchParams();
  if (redirectUri) {
    params.set("redirect_uri", redirectUri);
  }
  if (forwardTo) {
    params.set("forward_to", forwardTo);
  }
  const query = params.toString();
  return `${API_BASE_URL}/auth/login${query ? `?${query}` : ""}`;
};

export const exchangeCodeForToken = async ({ code, state, redirectUri }) => {
  const params = new URLSearchParams({ code, state, exchange_only: "true" });
  if (redirectUri) {
    params.set("redirect_uri", redirectUri);
  }
  const response = await fetch(`${API_BASE_URL}/auth/callback?${params.toString()}`, {
    credentials: "include",
  });
  return handleResponse(response);
};

export const fetchTopTracks = async ({ accessToken, limit = 20, timeRange = "medium_term" }) => {
  const params = new URLSearchParams({
    access_token: accessToken,
    limit: String(limit),
    time_range: timeRange,
  });
  const response = await fetch(`${API_BASE_URL}/auth/top-tracks?${params.toString()}`);
  return handleResponse(response);
};

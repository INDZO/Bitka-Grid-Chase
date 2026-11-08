function defaultApiBase() {
  if (typeof window === "undefined") {
    return "http://127.0.0.1:8000/api";
  }
  const isLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);
  return isLocal ? "http://127.0.0.1:8000/api" : `${window.location.origin}/api`;
}

const API_BASE = import.meta.env.VITE_API_BASE || defaultApiBase();

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Zahtev nije uspeo.");
  }
  return data;
}

export function createGame(payload) {
  return request("/games/", { method: "POST", body: JSON.stringify(payload) });
}

export function joinGame(roomCode, payload) {
  return request(`/games/${roomCode}/join/`, { method: "POST", body: JSON.stringify(payload) });
}

export function getGame(roomCode) {
  return request(`/games/${roomCode}/`);
}

export function moveGame(roomCode, payload) {
  return request(`/games/${roomCode}/move/`, { method: "POST", body: JSON.stringify(payload) });
}

export function timeoutGame(roomCode) {
  return request(`/games/${roomCode}/timeout/`, { method: "POST" });
}

export function getGameStats(roomCode) {
  return request(`/games/${roomCode}/stats/`);
}

export function getAlgorithmStats() {
  return request("/stats/algorithms/");
}

function defaultWsBase() {
  if (typeof window === "undefined") {
    return "ws://127.0.0.1:8000/ws";
  }
  const isLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);
  if (isLocal) {
    return "ws://127.0.0.1:8000/ws";
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws`;
}

const WS_BASE = import.meta.env.VITE_WS_BASE || defaultWsBase();

export function openGameSocket(roomCode, token, handlers) {
  const suffix = token ? `?token=${encodeURIComponent(token)}` : "";
  const socket = new WebSocket(`${WS_BASE}/game/${roomCode}/${suffix}`);

  socket.onopen = () => handlers.onOpen?.();
  socket.onclose = () => handlers.onClose?.();
  socket.onerror = () => handlers.onError?.("WebSocket veza nije dostupna.");
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === "state") {
      handlers.onState?.(message.payload);
    } else if (message.type === "error") {
      handlers.onError?.(message.message);
    }
  };

  return {
    sendMove(action) {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "move", player_token: token, action }));
        return true;
      }
      return false;
    },
    sendTimeout() {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "timeout" }));
        return true;
      }
      return false;
    },
    sync() {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "sync" }));
        return true;
      }
      return false;
    },
    close() {
      socket.close();
    },
  };
}

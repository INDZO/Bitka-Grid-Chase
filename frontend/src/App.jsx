import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import GamePage from "./pages/GamePage.jsx";
import StartPage from "./pages/StartPage.jsx";
import { createGame, getGame, joinGame, moveGame, timeoutGame } from "./services/api.js";
import { openGameSocket } from "./services/socket.js";

const DEFAULT_FORM = { mode: "1vAI", board_size: 6, skin: "Scout", ai_level: "astar" };
const DEFAULT_JOIN = { room_code: "", skin: "Guide" };
const SESSION_KEY = "bitka-grid-chase-session";
const DIRECTIONS = {
  up: [-1, 0],
  down: [1, 0],
  left: [0, -1],
  right: [0, 1],
};

function secondsUntil(deadline, serverOffsetMs = 0) {
  if (!deadline) return 0;
  return Math.max(0, (new Date(deadline).getTime() - (Date.now() + serverOffsetMs)) / 1000);
}

function keyOf(pos) {
  return `${pos[0]}:${pos[1]}`;
}

function asPosSet(items = []) {
  return new Set(items.map(keyOf));
}

function manhattan(a, b) {
  return Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]);
}

function getOccupiedHeroes(entities = {}, actorId) {
  return new Set(
    Object.entries(entities)
      .filter(([entityId, entity]) => (
        entityId !== actorId
        && entity.kind === "hero"
        && entity.active !== false
        && !entity.escaped
      ))
      .map(([, entity]) => keyOf(entity.pos))
  );
}

function isLegalTarget(game, actorId, target) {
  const state = game?.state;
  const actor = state?.entities?.[actorId];
  const board = state?.board;
  if (!state || !actor || !board) return false;
  if (!Array.isArray(target) || target.length !== 2) return false;
  if (target.some((value) => !Number.isInteger(value))) return false;
  if (target[0] < 0 || target[1] < 0 || target[0] >= board.size || target[1] >= board.size) return false;
  if (asPosSet(board.walls).has(keyOf(target))) return false;

  if (actor.kind === "hero") {
    if (keyOf(state.entities.monster?.pos || []) === keyOf(target)) return false;
    if (getOccupiedHeroes(state.entities, actorId).has(keyOf(target))) return false;
  }

  return true;
}

function getValidMoveDirections(game, actorId, isMyTurn) {
  if (!isMyTurn || !game?.state?.entities?.[actorId]) return new Set();
  const origin = game.state.entities[actorId].pos;
  return new Set(
    Object.entries(DIRECTIONS)
      .filter(([, delta]) => isLegalTarget(game, actorId, [origin[0] + delta[0], origin[1] + delta[1]]))
      .map(([direction]) => direction)
  );
}

function getValidMoveTargets(game, actorId, validMoveDirections) {
  const actor = game?.state?.entities?.[actorId];
  if (!actor) return new Set();
  return new Set(
    Object.entries(DIRECTIONS)
      .filter(([direction]) => validMoveDirections.has(direction))
      .map(([, delta]) => keyOf([actor.pos[0] + delta[0], actor.pos[1] + delta[1]]))
  );
}

function directionFromAdjacent(origin, target) {
  if (!origin || !target) return "";
  const delta = [target[0] - origin[0], target[1] - origin[1]];
  const match = Object.entries(DIRECTIONS).find(([, value]) => value[0] === delta[0] && value[1] === delta[1]);
  return match?.[0] || "";
}

function getValidTeleportTargets(game, actorId, isMyTurn, canTeleport) {
  const state = game?.state;
  const actor = state?.entities?.[actorId];
  const board = state?.board;
  if (!isMyTurn || !canTeleport || !actor || !board) return new Set();

  const origin = actor.pos;
  const targets = new Set();
  for (let row = 0; row < board.size; row += 1) {
    for (let col = 0; col < board.size; col += 1) {
      const target = [row, col];
      if (keyOf(target) !== keyOf(origin) && manhattan(origin, target) <= 2 && isLegalTarget(game, actorId, target)) {
        targets.add(keyOf(target));
      }
    }
  }
  return targets;
}

export default function App() {
  const [form, setForm] = useState(DEFAULT_FORM);
  const [joinForm, setJoinForm] = useState(DEFAULT_JOIN);
  const [game, setGame] = useState(null);
  const [session, setSession] = useState(null);
  const [socketState, setSocketState] = useState("offline");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [teleportMode, setTeleportMode] = useState(false);
  const [resolvingAction, setResolvingAction] = useState(false);
  const [tick, setTick] = useState(0);
  const socketRef = useRef(null);
  const timeoutRef = useRef("");

  useEffect(() => {
    const id = window.setInterval(() => setTick((value) => value + 1), 250);
    return () => window.clearInterval(id);
  }, []);

  const serverOffsetMs = useMemo(
    () => (game?.server_time ? new Date(game.server_time).getTime() - Date.now() : 0),
    [game?.server_time]
  );
  const turnLeft = secondsUntil(game?.state?.turn_deadline_at, serverOffsetMs);
  const totalLeft = secondsUntil(game?.state?.game_deadline_at, serverOffsetMs);
  const myEntityId = session?.player?.entity_id;
  const isMyTurn = Boolean(
    game?.state?.current_turn
      && game.state.current_turn === myEntityId
      && game.status === "playing"
      && !resolvingAction
  );
  const myEntity = myEntityId ? game?.state?.entities?.[myEntityId] : null;
  const canTeleport = isMyTurn && myEntity?.teleport_cooldown === 0;
  const validMoveDirections = useMemo(
    () => getValidMoveDirections(game, myEntityId, isMyTurn),
    [game, myEntityId, isMyTurn]
  );
  const validMoveTargets = useMemo(
    () => getValidMoveTargets(game, myEntityId, validMoveDirections),
    [game, myEntityId, validMoveDirections]
  );
  const validTeleportTargets = useMemo(
    () => getValidTeleportTargets(game, myEntityId, isMyTurn, canTeleport),
    [game, myEntityId, isMyTurn, canTeleport]
  );

  useEffect(() => {
    if (!game?.state || game.status !== "playing") return;
    if (resolvingAction) return;
    const expired = totalLeft <= 0 || turnLeft <= 0;
    const timeoutKind = totalLeft <= 0 ? "total" : "turn";
    const timeoutKey = `${game.room_code}:${game.state.turn_number}:${game.state.current_turn}:${timeoutKind}`;
    if (expired && timeoutRef.current !== timeoutKey) {
      timeoutRef.current = timeoutKey;
      const sent = socketRef.current?.sendTimeout();
      if (!sent) {
        timeoutGame(game.room_code)
          .then((payload) => {
            setError("");
            setGame(payload);
          })
          .catch((err) => setError(err.message));
      }
    }
  }, [tick, game, turnLeft, totalLeft, resolvingAction]);

  useEffect(() => () => socketRef.current?.close(), []);

  useEffect(() => {
    const raw = window.localStorage.getItem(SESSION_KEY);
    if (!raw) return;
    try {
      const saved = JSON.parse(raw);
      if (!saved?.room_code || !saved?.token || !saved?.player) return;
      setSession({ token: saved.token, player: saved.player });
      getGame(saved.room_code)
        .then((payload) => {
          setGame({ ...payload, current_player: saved.player });
          connectSocket(saved.room_code, saved.token);
        })
        .catch(() => window.localStorage.removeItem(SESSION_KEY));
    } catch {
      window.localStorage.removeItem(SESSION_KEY);
    }
  }, []);

  const connectSocket = (roomCode, token) => {
    socketRef.current?.close();
    socketRef.current = openGameSocket(roomCode, token, {
      onOpen: () => setSocketState("online"),
      onClose: () => setSocketState("offline"),
      onError: (message) => {
        setResolvingAction(false);
        setError(message);
      },
      onState: (payload) => {
        setError("");
        setResolvingAction(false);
        setGame((current) => ({ ...payload, current_player: current?.current_player || session?.player }));
      },
    });
  };

  const handleCreate = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = await createGame(form);
      setGame(payload);
      setResolvingAction(false);
      setSession({ token: payload.player_token, player: payload.current_player });
      window.localStorage.setItem(
        SESSION_KEY,
        JSON.stringify({ room_code: payload.room_code, token: payload.player_token, player: payload.current_player })
      );
      connectSocket(payload.room_code, payload.player_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleJoin = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = await joinGame(joinForm.room_code, { skin: joinForm.skin });
      setGame(payload);
      setResolvingAction(false);
      setSession({ token: payload.player_token, player: payload.current_player });
      window.localStorage.setItem(
        SESSION_KEY,
        JSON.stringify({ room_code: payload.room_code, token: payload.player_token, player: payload.current_player })
      );
      connectSocket(payload.room_code, payload.player_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const sendMove = useCallback(async (action) => {
    if (!isMyTurn) return;
    setResolvingAction(true);
    setTeleportMode(false);
    setError("");
    const sent = socketRef.current?.sendMove(action);
    if (sent || !game?.room_code || !session?.token) return;

    try {
      const payload = await moveGame(game.room_code, { player_token: session.token, action });
      setResolvingAction(false);
      setGame(payload);
    } catch (err) {
      setResolvingAction(false);
      setError(err.message);
    }
  }, [game?.room_code, isMyTurn, session?.token]);

  const sendSkip = useCallback(() => {
    sendMove({ type: "skip" });
  }, [sendMove]);

  const syncGame = async () => {
    if (!game?.room_code) return;
    setError("");
    const sent = socketRef.current?.sync();
    if (sent) return;
    try {
      const payload = await getGame(game.room_code);
      setResolvingAction(false);
      setGame((current) => ({ ...payload, current_player: current?.current_player || session?.player }));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleReplay = async () => {
    if (!game) return;
    const heroSkin = game.players?.find((player) => player.entity_id === "hero1")?.skin || form.skin;
    const replayForm = {
      mode: game.mode,
      board_size: game.board_size,
      skin: heroSkin,
      ai_level: game.mode === "1v1" ? "" : game.ai_level || "astar",
    };
    setBusy(true);
    setError("");
    timeoutRef.current = "";
    setTeleportMode(false);
    setResolvingAction(false);
    socketRef.current?.close();
    socketRef.current = null;
    window.localStorage.removeItem(SESSION_KEY);
    setSession(null);
    setSocketState("offline");
    setGame(null);
    try {
      const payload = await createGame(replayForm);
      setForm(replayForm);
      setGame(payload);
      setSession({ token: payload.player_token, player: payload.current_player });
      window.localStorage.setItem(
        SESSION_KEY,
        JSON.stringify({ room_code: payload.room_code, token: payload.player_token, player: payload.current_player })
      );
      connectSocket(payload.room_code, payload.player_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleCellClick = (target) => {
    if (teleportMode && canTeleport && validTeleportTargets.has(keyOf(target))) {
      sendMove({ type: "teleport", target });
      return;
    }

    if (!teleportMode && isMyTurn && myEntity?.pos) {
      const direction = directionFromAdjacent(myEntity.pos, target);
      if (direction && validMoveDirections.has(direction)) {
        sendMove({ type: "move", direction });
      }
    }
  };

  useEffect(() => {
    const handleKeyDown = (event) => {
      const tagName = event.target?.tagName;
      if (tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT") return;
      if (event.repeat) return;

      if ((event.key.toLowerCase() === "t" || event.code === "Space") && canTeleport) {
        event.preventDefault();
        setTeleportMode((value) => !value);
        return;
      }

      const keyMap = {
        arrowup: "up",
        w: "up",
        arrowdown: "down",
        s: "down",
        arrowleft: "left",
        a: "left",
        arrowright: "right",
        d: "right",
      };
      const direction = keyMap[event.key.toLowerCase()];
      if (direction && validMoveDirections.has(direction)) {
        event.preventDefault();
        sendMove({ type: "move", direction });
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [canTeleport, validMoveDirections, sendMove]);

  const resultTitle = useMemo(() => {
    if (game?.status !== "finished") return "";
    const winner = game.result?.winner;
    const role = game.current_player?.role || session?.player?.role;
    if (game.mode === "1v1" && role === "monster") {
      return winner === "monster" ? "Pobeda čudovišta" : "Poraz čudovišta";
    }
    return winner === "hero" ? "Pobeda heroja" : "Poraz heroja";
  }, [game, session?.player?.role]);

  const goHome = () => {
    socketRef.current?.close();
    socketRef.current = null;
    window.localStorage.removeItem(SESSION_KEY);
    setGame(null);
    setSession(null);
    setSocketState("offline");
    setTeleportMode(false);
    setResolvingAction(false);
    setError("");
  };

  if (!game) {
    return (
      <StartPage
        form={form}
        setForm={setForm}
        joinForm={joinForm}
        setJoinForm={setJoinForm}
        onCreate={handleCreate}
        onJoin={handleJoin}
        busy={busy}
        error={error}
      />
    );
  }

  return (
    <GamePage
      game={game}
      session={session}
      error={error}
      resultTitle={resultTitle}
      turnLeft={turnLeft}
      totalLeft={totalLeft}
      socketState={socketState}
      teleportMode={teleportMode}
      setTeleportMode={setTeleportMode}
      isMyTurn={isMyTurn}
      isResolving={resolvingAction}
      canTeleport={canTeleport}
      validMoveDirections={validMoveDirections}
      validMoveTargets={validMoveTargets}
      validTeleportTargets={validTeleportTargets}
      myEntityId={myEntityId}
      sendMove={sendMove}
      sendSkip={sendSkip}
      handleCellClick={handleCellClick}
      onSync={syncGame}
      onHome={goHome}
      onReplay={handleReplay}
    />
  );
}

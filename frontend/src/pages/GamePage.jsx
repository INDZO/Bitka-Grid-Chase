import { useState } from "react";
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Home, Keyboard, RefreshCw, StepForward, Zap } from "lucide-react";
import AIDebugPanel, { getLatestAiDebug } from "../components/AIDebugPanel.jsx";
import Board from "../components/Board.jsx";
import EventFeed from "../components/EventFeed.jsx";
import GameOverPanel from "../components/GameOverPanel.jsx";
import Hud from "../components/Hud.jsx";
import StatsPanel from "../components/StatsPanel.jsx";
import WaitingRoom from "../components/WaitingRoom.jsx";

function entityLabel(entities, entityId) {
  const entity = entities?.[entityId];
  if (!entity) {
    if (entityId === "monster") return "Čudovište";
    if (entityId?.startsWith("hero")) return "Heroj";
    return "čekanje";
  }
  if (entity.kind === "hero") return entity.skin || "Heroj";
  if (entity.ai) return entity.name || "AI čudovište";
  return "Čudovište";
}

function turnMessage({ game, isMyTurn, isAiTurn, isResolving, currentLabel, myLabel }) {
  if (isResolving) {
    return game.mode === "1v1" ? "Potez se obrađuje..." : "AI razmišlja...";
  }
  if (isMyTurn) return `Tvoj potez: ${myLabel}`;
  if (isAiTurn) return `AI je na potezu: ${currentLabel} razmišlja...`;
  if (game.status === "waiting") return `Podeli kôd ${game.room_code}`;
  if (game.mode === "1vAI") return `${currentLabel} je u lovu`;
  return `${currentLabel} je na potezu`;
}

export default function GamePage({
  game,
  session,
  error,
  resultTitle,
  turnLeft,
  totalLeft,
  socketState,
  teleportMode,
  setTeleportMode,
  isMyTurn,
  isResolving,
  canTeleport,
  validMoveDirections,
  validMoveTargets,
  validTeleportTargets,
  myEntityId,
  sendMove,
  sendSkip,
  handleCellClick,
  onSync,
  onHome,
  onReplay,
}) {
  const [debugEnabled, setDebugEnabled] = useState(false);
  const [infoTab, setInfoTab] = useState("stats");
  const entities = game.state?.entities || {};
  const monsterName = entityLabel(entities, "monster");
  const title =
    game.status === "finished"
      ? resultTitle
      : game.status === "waiting"
        ? "Čekanje igrača kod kapije"
        : game.mode === "1vAI"
          ? `1vAI protiv ${monsterName}`
          : game.mode === "2vAI"
            ? `2vAI protiv ${monsterName}`
            : "Duel u postaji";
  const currentLabel = entityLabel(entities, game.state?.current_turn);
  const myLabel = entityLabel(entities, myEntityId);
  const roomLabel = game.mode === "1vAI" ? "solo partija" : `kôd ${game.room_code}`;
  const latestDebug = getLatestAiDebug(game);
  const debugOverlay = debugEnabled ? latestDebug : null;
  const currentEntity = game.state?.current_turn ? entities[game.state.current_turn] : null;
  const isAiTurn = game.status === "playing" && Boolean(currentEntity?.ai);
  const controlsLocked = !isMyTurn || isResolving;
  const boardStatusMessage = isResolving
    ? game.mode === "1v1" ? "Potez se obrađuje..." : "AI razmišlja..."
    : isAiTurn
      ? `${currentLabel} razmišlja...`
      : !isMyTurn && game.status === "playing"
        ? `${currentLabel} je na potezu`
        : "";
  const currentTurnMessage = turnMessage({ game, isMyTurn, isAiTurn, isResolving, currentLabel, myLabel });

  return (
    <main className="app game-app">
      <header className="game-header">
        <button className="icon-btn" type="button" onClick={onHome} title="Glavni meni">
          <Home size={18} />
        </button>
        <div className="game-title-block">
          <span className="eyebrow">Outpost AV Club / Grid Chase</span>
          <h1>{title}</h1>
          <div className="header-meta">
            <span>{roomLabel}</span>
            <span>{socketState === "online" ? "veza online" : "veza offline"}</span>
          </div>
        </div>
        <button
          className="sync-btn header-action"
          type="button"
          onClick={onSync}
          title="Ponovo učitava trenutno stanje partije sa servera."
        >
          <RefreshCw size={18} />
          <span>Sinhronizuj</span>
        </button>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {game.status === "waiting" && <WaitingRoom game={game} socketState={socketState} />}

      {game.status !== "waiting" && (
        <section className={game.status === "finished" ? "game-layout finished-layout" : "game-layout"}>
          <Hud game={game} session={session} turnLeft={turnLeft} totalLeft={totalLeft} socketState={socketState} />
          <Board
            state={game.state}
            teleportMode={teleportMode}
            validMoveTargets={validMoveTargets}
            validTeleportTargets={validTeleportTargets}
            inputDisabled={controlsLocked}
            statusMessage={boardStatusMessage}
            currentTurn={game.state?.current_turn}
            myEntityId={myEntityId}
            debugOverlay={debugOverlay}
            onCellClick={handleCellClick}
          />
          <section className="control-panel">
            <section className="action-panel">
              <div className="panel-title">Kontrole</div>
              <div className={isResolving || isAiTurn ? "turn-note ai-thinking" : isMyTurn ? "turn-note active" : "turn-note"}>
                {currentTurnMessage}
              </div>
              <div className={teleportMode ? "teleport-readout active" : "teleport-readout"}>
                Teleport {teleportMode ? "aktiviran" : canTeleport ? "spreman" : "na hlađenju"}
              </div>
              <div className="action-buttons">
                <button
                  className={teleportMode ? "mobile-teleport-btn active" : "mobile-teleport-btn"}
                  type="button"
                  disabled={!canTeleport || isResolving}
                  onClick={() => setTeleportMode((value) => !value)}
                >
                  <Zap size={18} /> {teleportMode ? "Teleport aktiviran" : canTeleport ? "Aktiviraj teleport" : "Teleport na hlađenju"}
                </button>
                <button className="skip-btn" type="button" disabled={!isMyTurn || isResolving} onClick={sendSkip}>
                  <StepForward size={18} /> Preskoči potez
                </button>
              </div>
              <div className="keyboard-hint">
                <Keyboard size={16} /> Koristi strelice/WASD za kretanje, T ili Space za teleport.
              </div>
              <div className="dpad" aria-label="Kontrole za dodir">
                <button type="button" disabled={controlsLocked || !validMoveDirections.has("up")} onClick={() => sendMove({ type: "move", direction: "up" })} title="Gore"><ArrowUp /></button>
                <button type="button" disabled={controlsLocked || !validMoveDirections.has("left")} onClick={() => sendMove({ type: "move", direction: "left" })} title="Levo"><ArrowLeft /></button>
                <button type="button" disabled={!canTeleport || isResolving} onClick={() => setTeleportMode((value) => !value)} className={teleportMode ? "dpad-teleport active" : "dpad-teleport"} title="Teleport"><Zap /></button>
                <button type="button" disabled={controlsLocked || !validMoveDirections.has("right")} onClick={() => sendMove({ type: "move", direction: "right" })} title="Desno"><ArrowRight /></button>
                <button type="button" disabled={controlsLocked || !validMoveDirections.has("down")} onClick={() => sendMove({ type: "move", direction: "down" })} title="Dole"><ArrowDown /></button>
              </div>
            </section>

            <div className="info-tabs" role="tablist" aria-label="Pregled partije">
              <button type="button" className={infoTab === "stats" ? "active" : ""} aria-selected={infoTab === "stats"} onClick={() => setInfoTab("stats")}>Statistika</button>
              {game.mode !== "1v1" && (
                <button type="button" className={infoTab === "debug" ? "active" : ""} aria-selected={infoTab === "debug"} onClick={() => setInfoTab("debug")}>Debug AI</button>
              )}
              <button type="button" className={infoTab === "log" ? "active" : ""} aria-selected={infoTab === "log"} onClick={() => setInfoTab("log")}>Dnevnik</button>
            </div>
            {infoTab === "stats" && <StatsPanel game={game} />}
            {infoTab === "debug" && game.mode !== "1v1" && <AIDebugPanel game={game} enabled={debugEnabled} setEnabled={setDebugEnabled} />}
            {infoTab === "log" && <EventFeed state={game.state} />}
          </section>
        </section>
      )}
      {game.status === "finished" && (
        <GameOverPanel game={game} resultTitle={resultTitle} onHome={onHome} onReplay={onReplay} />
      )}
    </main>
  );
}

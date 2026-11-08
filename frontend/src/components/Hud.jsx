import { Clock, RadioTower, Zap } from "lucide-react";

function formatSeconds(value) {
  const safe = Math.max(0, Math.ceil(value || 0));
  const minutes = Math.floor(safe / 60);
  const seconds = String(safe % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export default function Hud({ game, session, turnLeft, totalLeft, socketState }) {
  const state = game?.state || {};
  const entities = state.entities || {};
  const current = state.current_turn ? entities[state.current_turn] : null;
  const heroMemories = state.board?.memories?.filter((memory) => memory.collected).length || 0;
  const totalMemories = state.board?.memories?.length || 0;
  const myEntity = session?.player?.entity_id ? entities[session.player.entity_id] : null;
  const monster = entities.monster;
  const isSoloAi = game?.mode === "1vAI";
  const monsterName = monster?.ai ? monster.name : "Čudovište";
  const currentName = current?.kind === "hero" ? current.skin : (current?.ai ? current.name : "Čudovište");
  const connectionText = isSoloAi ? "lokalna partija" : (socketState === "online" ? "online" : "offline");

  return (
    <aside className="hud">
      <div className="hud-row">
        <span className="hud-label"><RadioTower size={16} /> {isSoloAi ? "Režim" : "Kôd sobe"}</span>
        <strong>{isSoloAi ? "1vAI" : game?.room_code || "------"}</strong>
      </div>
      <div className="hud-row">
        <span className="hud-label">Protivnik</span>
        <strong>{monsterName || "Čudovište"}</strong>
      </div>
      <div className="hud-row">
        <span className="hud-label"><Clock size={16} /> Partija</span>
        <strong>{formatSeconds(totalLeft)}</strong>
      </div>
      <div className="hud-row">
        <span className="hud-label"><Clock size={16} /> Potez</span>
        <strong>{formatSeconds(turnLeft)}</strong>
      </div>
      <div className="hud-row">
        <span className="hud-label">Na potezu</span>
        <strong>{state.current_turn ? `${currentName || "Heroj"}${current?.ai ? " / AI" : ""}` : "čekanje"}</strong>
      </div>
      <div className="hud-row">
        <span className="hud-label">Sećanja</span>
        <strong>{heroMemories}/{totalMemories}</strong>
      </div>
      <div className="hud-row">
        <span className="hud-label"><Zap size={16} /> Teleport heroja</span>
        <strong>{myEntity ? myEntity.teleport_cooldown : "-"}</strong>
      </div>
      <div className="hud-row">
        <span className="hud-label"><Zap size={16} /> Teleport čudovišta</span>
        <strong>{monster ? monster.teleport_cooldown : "-"}</strong>
      </div>
      <div className="hud-row">
        <span className="hud-label">Veza</span>
        <strong>{connectionText}</strong>
      </div>
    </aside>
  );
}

import { LogIn, Plus, Radio } from "lucide-react";
import { useEffect, useState } from "react";
import PixelSprite from "./PixelSprite.jsx";

const MODES = ["1vAI", "1v1", "2vAI"];
const SIZES = [5, 6, 7, 8];
const SKINS = ["Scout", "Guide", "Runner", "Builder", "Ranger", "Pilot"];
const AI_LEVELS = [
  { value: "minmax", label: "Sentinel / MinMax" },
  { value: "alphabeta", label: "AlfaAI / Alpha-Beta" },
  { value: "astar", label: "ShadowMonster / A*" },
  { value: "mcts", label: "MindFlyer / MCTS" },
];

export default function SetupPanel({ form, setForm, joinForm, setJoinForm, onCreate, onJoin, busy }) {
  const [onlineFlow, setOnlineFlow] = useState("create");
  const usesAi = form.mode !== "1v1";
  const isSoloAi = form.mode === "1vAI";
  const isDuel = form.mode === "1v1";
  const selectedAi = AI_LEVELS.find((level) => level.value === form.ai_level) || AI_LEVELS[2];

  useEffect(() => {
    if (isSoloAi) {
      setOnlineFlow("create");
    }
  }, [isSoloAi]);

  return (
    <section className={`${isSoloAi ? "setup-grid solo" : "setup-grid"} online-flow-${onlineFlow}`}>
      {!isSoloAi && (
        <div className="online-flow-toggle" aria-label="Izbor online toka">
          <button
            type="button"
            className={onlineFlow === "create" ? "active" : ""}
            onClick={() => setOnlineFlow("create")}
          >
            Kreiraj sobu
          </button>
          <button
            type="button"
            className={onlineFlow === "join" ? "active" : ""}
            onClick={() => setOnlineFlow("join")}
          >
            Uđi u sobu
          </button>
        </div>
      )}
      <form className="panel setup-main setup-create-panel" onSubmit={onCreate}>
        <div className="panel-title"><Plus size={18} /> {isSoloAi ? "Solo partija" : "Online partija"}</div>
        <div className="field-group">
          <span className="field-label">Režim</span>
          <div className="segmented">
            {MODES.map((mode) => (
              <button
                type="button"
                className={form.mode === mode ? "active" : ""}
                key={mode}
                onClick={() => setForm((current) => ({ ...current, mode, ai_level: mode === "1v1" ? "" : current.ai_level || "astar" }))}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>
        <div className="field-group">
          <span className="field-label">Veličina mape</span>
          <div className="segmented">
            {SIZES.map((size) => (
              <button
                type="button"
                className={form.board_size === size ? "active" : ""}
                key={size}
                onClick={() => setForm((current) => ({ ...current, board_size: size }))}
              >
                {size}x{size}
              </button>
            ))}
          </div>
        </div>
        <div className="field-group">
          <span className="field-label">Izgled heroja</span>
          <div className="skin-grid">
            {SKINS.map((skin) => (
              <button
                type="button"
                key={skin}
                className={form.skin === skin ? "skin-card active" : "skin-card"}
                onClick={() => setForm((current) => ({ ...current, skin }))}
              >
                <PixelSprite type="hero" skin={skin} label={skin} />
                <span>{skin}</span>
              </button>
            ))}
          </div>
        </div>
        {usesAi && (
          <div className="field-group">
            <span className="field-label">AI protivnik</span>
            <div className="ai-grid">
              {AI_LEVELS.map((level) => (
                <button
                  type="button"
                  key={level.value}
                  className={form.ai_level === level.value ? "ai-card active" : "ai-card"}
                  onClick={() => setForm((current) => ({ ...current, ai_level: level.value }))}
                >
                  <PixelSprite type="monster" variant={level.label.split(" / ")[0]} label={level.label} />
                  <span>{level.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}
        <button className="primary-btn" type="submit" disabled={busy}>
          <Radio size={18} /> {busy ? "Otvaranje kapije..." : isSoloAi ? `Počni protiv ${selectedAi.label.split(" / ")[0]}` : "Kreiraj kôd sobe"}
        </button>
      </form>

      {!isSoloAi && (
        <form className="panel join-panel setup-join-panel" onSubmit={onJoin}>
          <div className="panel-title"><LogIn size={18} /> Uđi preko koda</div>
          <label>
            Kôd sobe
            <input
              maxLength={6}
              value={joinForm.room_code}
              onChange={(event) => setJoinForm((current) => ({ ...current, room_code: event.target.value.toUpperCase() }))}
              placeholder="ABC123"
            />
          </label>
          {isDuel ? (
            <div className="monster-join-card">
              <PixelSprite type="monster" variant="Player Monster" label="Čudovište" />
              <span>Drugi igrač ulazi kao čudovište.</span>
            </div>
          ) : (
            <div className="field-group">
              <span className="field-label">Izgled drugog heroja</span>
              <div className="skin-grid compact">
                {SKINS.map((skin) => (
                  <button
                    type="button"
                    key={skin}
                    className={joinForm.skin === skin ? "skin-card active" : "skin-card"}
                    onClick={() => setJoinForm((current) => ({ ...current, skin }))}
                  >
                    <PixelSprite type="hero" skin={skin} label={skin} />
                    <span>{skin}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          <button className="primary-btn" type="submit" disabled={busy}>
            <LogIn size={18} /> {busy ? "Povezivanje..." : isDuel ? "Uđi kao čudovište" : "Uđi u online partiju"}
          </button>
        </form>
      )}
    </section>
  );
}

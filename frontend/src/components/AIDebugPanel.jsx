import { BrainCircuit } from "lucide-react";

function actionText(action = {}) {
  const directions = { UP: "gore", DOWN: "dole", LEFT: "levo", RIGHT: "desno", up: "gore", down: "dole", left: "levo", right: "desno" };
  if (action.type === "move") return `pomeranje ${directions[action.direction] || action.direction}`;
  if (action.type === "teleport") return `teleport [${action.target?.join(", ")}]`;
  if (action.type === "timeout") return "istek vremena";
  if (action.type === "skip") return "preskočen potez";
  return action.type || "istek vremena";
}

function pct(value) {
  if (value === undefined || value === null) return "-";
  return `${Math.round(value * 100)}%`;
}

function posText(pos) {
  return Array.isArray(pos) ? `[${pos.join(", ")}]` : "-";
}

function decisionReason(debug) {
  if (debug?.reason) return debug.reason;
  if (debug?.selected_action?.type === "teleport") return "Teleport je skratio putanju do najbližeg heroja.";
  if (debug?.path?.length > 1) return "Izabrana je najkraća pronađena putanja ka heroju.";
  if (debug?.use_alpha_beta) return "Alpha-Beta je odbacila slabije grane i izabrala najbolji score.";
  if (debug?.algorithm === "MinMax") return "MinMax je uporedio kandidate po proceni pozicije.";
  if (debug?.algorithm === "MCTS") return "MCTS je izabrao potez sa najboljim prosečnim rollout rezultatom.";
  return "AI je uporedio dostupne poteze i izabrao najbolji kandidat.";
}

function candidateValue(candidate) {
  if (candidate.winrate !== undefined) return `${candidate.visits || 0} poseta / ${pct(candidate.winrate)}`;
  if (candidate.heuristic !== undefined) return `h=${candidate.heuristic}`;
  if (candidate.score !== undefined && candidate.score !== null) return `score=${candidate.score}`;
  if (candidate.distance_after !== undefined) return `udaljenost=${candidate.distance_after}`;
  return "-";
}

export function getLatestAiDebug(game) {
  const moves = game?.ai_stats?.moves || [];
  const latest = moves[moves.length - 1];
  if (!latest) return null;
  const debug = latest.debug || {};
  const selected = latest.selected_move || debug.selected_action || {};
  const selectedCandidate = (debug.candidates || []).find(
    (candidate) => JSON.stringify(candidate.action) === JSON.stringify(selected)
  );
  return {
    ...debug,
    algorithm: latest.algorithm,
    time_ms: latest.decision_ms,
    nodes_expanded: latest.nodes,
    selected_action: selected,
    selected_target: selectedCandidate?.target || debug.path?.[1] || selected.target || null,
    used_teleport: latest.used_teleport,
  };
}

export default function AIDebugPanel({ game, enabled, setEnabled }) {
  const debug = getLatestAiDebug(game);
  const candidates = debug?.candidates || [];

  return (
    <section className={enabled ? "ai-debug-panel active" : "ai-debug-panel"}>
      <label className="debug-toggle">
        <input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />
        <span><BrainCircuit size={16} /> Debug AI</span>
      </label>

      {!enabled && <div className="empty-log">Uključi Debug AI da vidiš pretragu, kandidate i označena polja na mapi.</div>}
      {enabled && !debug && <div className="empty-log">Debug podaci će se pojaviti posle AI poteza.</div>}
      {enabled && debug && (
        <>
          <div className="debug-metrics">
            <span>Algoritam</span><strong>{debug.algorithm}</strong>
            <span>Vreme odlučivanja</span><strong>{debug.time_ms ?? 0} ms</strong>
            <span>Obrađena stanja</span><strong>{debug.nodes_expanded ?? 0}</strong>
            <span>Teleport</span><strong>{debug.used_teleport ? "da" : "ne"}</strong>
            <span>Ciljno polje</span><strong>{posText(debug.selected_target)}</strong>
            {debug.depth && <><span>Dubina</span><strong>{debug.depth}</strong></>}
            {debug.rollouts !== undefined && <><span>Rollouts</span><strong>{debug.rollouts}</strong></>}
          </div>
          <div className="debug-choice">
            <span>Odabrani potez</span>
            <strong>{actionText(debug.selected_action)}</strong>
          </div>
          <div className="debug-choice">
            <span>Razlog</span>
            <strong>{decisionReason(debug)}</strong>
          </div>
          {debug.path?.length > 0 && (
            <div className="debug-path">
              <span>A* putanja</span>
              <strong>{debug.path.map((pos) => `[${pos.join(",")}]`).join(" -> ")}</strong>
            </div>
          )}
          <div className="candidate-list">
            <div className="sub-panel-title">Kandidati</div>
            {candidates.length === 0 && <span className="empty-log">Nema kandidata za poslednji AI potez.</span>}
            {candidates.slice(0, 5).map((candidate) => (
              <div className="candidate-row" key={`${candidate.rank}-${actionText(candidate.action)}`}>
                <span>#{candidate.rank} {actionText(candidate.action)}</span>
                <strong>{candidateValue(candidate)}</strong>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

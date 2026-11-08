import { useEffect, useState } from "react";
import { getAlgorithmStats } from "../services/api.js";

function actionText(action = {}) {
  const directions = { UP: "gore", DOWN: "dole", LEFT: "levo", RIGHT: "desno", up: "gore", down: "dole", left: "levo", right: "desno" };
  if (action.type === "move") return directions[action.direction] || action.direction;
  if (action.type === "teleport") return `teleport [${action.target?.join(", ")}]`;
  if (action.type === "timeout") return "istek vremena";
  if (action.type === "skip") return "preskočen potez";
  return action.type || "-";
}

function formatMs(value = 0) {
  return `${Number(value || 0).toFixed(3)} ms`;
}

function formatDuration(ms = 0) {
  const totalSeconds = Math.max(0, Math.round(Number(ms || 0) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function winnerText(winner) {
  if (winner === "hero") return "Heroji";
  if (winner === "monster") return "Čudovište";
  return "";
}

function boolText(value = false) {
  return value ? "da" : "ne";
}

function cleanReason(reason = "", game) {
  const entities = game?.state?.entities || {};
  return reason
    .replaceAll("hero1", entities.hero1?.skin || "Heroj")
    .replaceAll("hero2", entities.hero2?.skin || "Drugi heroj")
    .replaceAll("PlayerMonster", "Čudovište")
    .replaceAll("playerMonster", "Čudovište");
}

export default function StatsPanel({ game }) {
  const stats = game?.ai_stats;
  const summary = stats?.summary || {};
  const moves = stats?.moves || [];
  const latestMove = moves[moves.length - 1];
  const match = game?.match_stats || {};
  const isFinished = game?.status === "finished";
  const [algorithmRows, setAlgorithmRows] = useState([]);

  useEffect(() => {
    if (game?.mode === "1v1") return;
    getAlgorithmStats()
      .then((payload) => setAlgorithmRows(payload.algorithms || []))
      .catch(() => setAlgorithmRows([]));
  }, [game?.mode, summary.move_count]);

  return (
    <section className="stats-panel">
      <div className="panel-title">Statistika</div>
      <div className="stat-section">
        <div className="sub-panel-title">Trenutna partija</div>
        <div className="stats-grid">
          <span>Potezi</span><strong>{match.total_moves || 0}</strong>
          <span>Trajanje</span><strong>{formatDuration(match.duration_ms)}</strong>
          <span>Sakupljena sećanja</span><strong>{match.memories_collected || 0}/{match.memories_total || 0}</strong>
          <span>Teleporti</span><strong>{match.teleports_used || 0}</strong>
          <span>Vines efekti</span><strong>{match.vines_hits || 0}</strong>
          <span>Pomeranja portala</span><strong>{match.portal_shifts || 0}</strong>
          <span>Istek vremena</span><strong>{match.timeouts || 0}</strong>
          {isFinished && <><span>Pobednik</span><strong>{winnerText(match.winner)}</strong></>}
          {isFinished && match.reason && <><span>Razlog kraja</span><strong>{cleanReason(match.reason, game)}</strong></>}
        </div>
      </div>

      {game?.mode !== "1v1" && (
        <>
          <div className="stat-section">
            <div className="sub-panel-title">Poslednji AI potez</div>
            {latestMove ? (
              <div className="stats-grid compact-stats">
                <span>Algoritam</span><strong>{latestMove.algorithm}</strong>
                <span>Vreme</span><strong>{formatMs(latestMove.decision_ms)}</strong>
                <span>Čvorovi / stanja</span><strong>{latestMove.nodes || 0}</strong>
                <span>Odabrano</span><strong>{actionText(latestMove.selected_move)}</strong>
                <span>Teleport</span><strong>{boolText(latestMove.used_teleport)}</strong>
              </div>
            ) : (
              <span className="empty-log">AI još nije odigrao potez.</span>
            )}
          </div>

          <div className="stat-section">
            <div className="sub-panel-title">AI ukupno</div>
            <div className="stats-grid compact-stats">
              <span>Ukupno vreme</span><strong>{formatMs(summary.total_time_ms)}</strong>
              <span>Prosečno vreme</span><strong>{formatMs(summary.avg_time_ms)}</strong>
              <span>Ukupno čvorova</span><strong>{summary.total_nodes || 0}</strong>
              <span>Prosečno čvorova</span><strong>{Number(summary.avg_nodes || 0).toFixed(1)}</strong>
              <span>AI poteza</span><strong>{summary.move_count || 0}</strong>
            </div>
            <div className="move-log">
              {moves.length === 0 && <span className="empty-log">AI još nije odigrao.</span>}
              {moves.slice(-5).map((move) => (
                <div className="move-log-row" key={`${move.move_number}-${move.decision_ms}`}>
                  <span>#{move.move_number} {move.algorithm}</span>
                  <strong>{actionText(move.selected_move)} / {move.nodes || 0}</strong>
                </div>
              ))}
            </div>
          </div>

          {algorithmRows.length > 0 && (
            <div className="stat-section">
              <div className="sub-panel-title">Agregatno</div>
              <div className="algorithm-table">
                {algorithmRows.map((row, index) => (
                  <div className="algorithm-row" key={`${row.algorithm}-${index}`}>
                    <span>{row.algorithm}</span>
                    <strong>{formatMs(row.avg_time_ms)} / {row.total_nodes || 0}{row.finished_games ? ` / ${Math.round(row.win_rate * 100)}%` : ""}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

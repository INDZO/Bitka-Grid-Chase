import { Home, RotateCcw } from "lucide-react";
import PixelSprite from "./PixelSprite.jsx";

function formatDuration(ms = 0) {
  const total = Math.max(0, Math.round(ms / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = String(total % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function playerWon(game) {
  const winner = game.result?.winner;
  if (game.mode === "1v1" && game.current_player?.role === "monster") {
    return winner === "monster";
  }
  return winner === "hero";
}

function winnerText(winner) {
  if (winner === "hero") return "Heroji";
  if (winner === "monster") return "Čudovište";
  return "-";
}

function cleanReason(reason = "", game) {
  const entities = game?.state?.entities || {};
  return reason
    .replaceAll("hero1", entities.hero1?.skin || "Heroj")
    .replaceAll("hero2", entities.hero2?.skin || "Drugi heroj")
    .replaceAll("PlayerMonster", "Čudovište")
    .replaceAll("playerMonster", "Čudovište");
}

export default function GameOverPanel({ game, resultTitle, onHome, onReplay }) {
  const won = playerWon(game);
  const stats = game.match_stats || {};
  const replayLabel = game.mode === "1vAI" ? "Nova partija" : "Nova soba";
  const reason = cleanReason(game.result?.reason || stats.reason || "Partija je završena.", game);

  return (
    <div className="game-over-overlay" role="dialog" aria-modal="true" aria-label={won ? "Pobeda" : "Poraz"}>
      <section className={won ? "game-over-panel victory" : "game-over-panel defeat"}>
        <PixelSprite type={won ? "victory" : "defeat"} label={won ? "Pobeda" : "Poraz"} />
        <div>
          <div className="panel-title">{won ? "Pobeda" : "Poraz"}</div>
          <h2>{resultTitle}</h2>
          <p>{reason}</p>
        </div>
        <div className="end-stats-grid">
          <span>Pobednik</span><strong>{winnerText(game.result?.winner || stats.winner)}</strong>
          <span>Trajanje</span><strong>{formatDuration(stats.duration_ms)}</strong>
          <span>Potezi</span><strong>{stats.total_moves || 0}</strong>
          <span>Sećanja</span><strong>{stats.memories_collected || 0}/{stats.memories_total || 0}</strong>
          <span>Teleporti</span><strong>{stats.teleports_used || 0}</strong>
          <span>Vines efekti</span><strong>{stats.vines_hits || 0}</strong>
          <span>Pomeranja portala</span><strong>{stats.portal_shifts || 0}</strong>
        </div>
        <div className="end-actions">
          <button className="primary-btn" type="button" onClick={onReplay}>
            <RotateCcw size={18} /> {replayLabel}
          </button>
          <button className="secondary-btn" type="button" onClick={onHome}>
            <Home size={18} /> Glavni meni
          </button>
        </div>
      </section>
    </div>
  );
}

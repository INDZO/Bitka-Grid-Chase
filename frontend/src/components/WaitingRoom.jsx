import { Copy, RadioTower } from "lucide-react";

export default function WaitingRoom({ game, socketState }) {
  const playersNeeded = game.mode === "1vAI" ? 1 : 2;
  const joined = game.players?.length || 1;
  const copyCode = () => navigator.clipboard?.writeText(game.room_code);

  return (
    <section className="waiting-room">
      <div className="panel-title"><RadioTower size={18} /> Čekaonica</div>
      <h2>{game.mode === "1v1" ? "Čekanje igrača čudovišta" : "Čekanje drugog heroja"}</h2>
      <p>Kôd sobe je spreman. Drugi igrač bira isti režim, unosi kôd i ulazi u partiju.</p>
      <button className="room-code-card" type="button" onClick={copyCode} title="Kopiraj kôd sobe">
        <span>{game.room_code}</span>
        <Copy size={18} />
      </button>
      <div className="waiting-stats">
        <span>Igrači</span><strong>{joined}/{playersNeeded}</strong>
        <span>Signal</span><strong>{socketState === "online" ? "stabilan" : "offline"}</strong>
        <span>Mapa</span><strong>{game.board_size}x{game.board_size}</strong>
      </div>
    </section>
  );
}

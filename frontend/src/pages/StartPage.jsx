import { BookOpen, Gamepad2 } from "lucide-react";
import { useState } from "react";
import SetupPanel from "../components/SetupPanel.jsx";
import PixelSprite from "../components/PixelSprite.jsx";

const RULES = [
  "Sakupi sva sećanja pre ulaska u portal.",
  "Wall of Darkness blokira sve, a vines usporava samo heroje.",
  "Teleport radi do 2 polja i vraća se posle hlađenja.",
  "U online režimima drugi igrač ulazi preko koda sobe.",
];

export default function StartPage({ form, setForm, joinForm, setJoinForm, onCreate, onJoin, busy, error }) {
  const [setupOpen, setSetupOpen] = useState(false);
  const [rulesOpen, setRulesOpen] = useState(false);

  return (
    <main className="app start-app">
      <section className="hero-screen">
        <div className="lights-row" aria-hidden="true">
          {Array.from({ length: 13 }).map((_, index) => <span key={index} />)}
        </div>
        <div className="title-stack">
          <div className="st-logo" aria-label="Grid Chase">
            <span>Search</span>
            <span>Lab</span>
          </div>
          <h1>Bitka Grid Chase</h1>
          <p>Outpost noću, nestabilan portal, sećanja po mapi i AI čudovište koje prati svaki korak kroz Grid Chase.</p>
          <div className="title-actions">
            <button className="primary-btn" type="button" onClick={() => setSetupOpen((value) => !value)}>
              <Gamepad2 size={18} /> {setupOpen ? "Zatvori podešavanja" : "Pokreni igru"}
            </button>
            <button className="secondary-btn" type="button" onClick={() => setRulesOpen((value) => !value)}>
              <BookOpen size={18} /> Kako se igra
            </button>
          </div>
          {rulesOpen && (
            <div className="how-to-panel">
              {RULES.map((rule) => <span key={rule}>{rule}</span>)}
            </div>
          )}
        </div>
        <div className={`landing-side${setupOpen ? " setup-open" : ""}`}>
          {setupOpen ? (
            <SetupPanel form={form} setForm={setForm} joinForm={joinForm} setJoinForm={setJoinForm} onCreate={onCreate} onJoin={onJoin} busy={busy} />
          ) : (
            <section className="landing-card" aria-label="Pregled igre">
              <div className="panel-title">Signal iz postaje</div>
              <div className="pixel-diorama" aria-hidden="true">
                <span className="diorama-cell wall" />
                <span className="diorama-cell" />
                <span className="diorama-cell memory"><PixelSprite type="memory" label="Sećanje" /></span>
                <span className="diorama-cell" />
                <span className="diorama-cell vines" />
                <span className="diorama-cell hero"><PixelSprite type="hero" skin="Scout" label="Scout" /></span>
                <span className="diorama-cell portal"><PixelSprite type="portal" label="Portal" /></span>
                <span className="diorama-cell monster"><PixelSprite type="monster" variant="ShadowMonster" label="ShadowMonster" /></span>
                <span className="diorama-cell wall" />
              </div>
              <div className="landing-stat-grid">
                <span>Režimi</span><strong>1vAI / 1v1 / 2vAI</strong>
                <span>Mapa</span><strong>5x5 do 8x8</strong>
                <span>AI</span><strong>MinMax, A*, MCTS</strong>
                <span>Online</span><strong>kôd sobe</strong>
              </div>
              <div className="landing-brief">
                <strong>Cilj partije</strong>
                <span>Preživi poteru, sakupi sećanja i pronađi portal pre nego što signal nestane.</span>
              </div>
            </section>
          )}
        </div>
        {error && <div className="error-banner">{error}</div>}
      </section>
    </main>
  );
}


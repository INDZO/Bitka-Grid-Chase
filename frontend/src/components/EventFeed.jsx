import { ListTree } from "lucide-react";

function entityLabel(state, entityId) {
  const entity = state?.entities?.[entityId];
  if (!entity) {
    if (entityId === "monster") return "Čudovište";
    if (entityId?.startsWith("hero")) return "Heroj";
    return "Signal";
  }
  if (entity.kind === "hero") return entity.skin || entityId;
  if (entity.ai) return entity.name || "AI čudovište";
  return "Čudovište";
}

function formatEvent(event, state) {
  const actor = entityLabel(state, event.entity);
  switch (event.type) {
    case "game_started":
      return "Kapija se otvorila";
    case "move":
      return `${actor} se pomerio`;
    case "teleport":
      return `${actor} je prošao kroz procep`;
    case "memory_collected":
      return `${actor} je našao sećanje`;
    case "vines_snared":
      return `${actor} je uhvaćen u vines`;
    case "vines_skip":
      return "Heroj je zarobljen u vines i preskače potez.";
    case "vines_grew_on_hero":
      return `Vines su stigle do ${actor}`;
    case "vines_grew":
      return "Grid Chase se širi";
    case "portal_shifted":
      return "Portal je promenio mesto";
    case "portal_entered":
      return `${actor} je ušao u portal`;
    case "captured":
      return `${actor} je uhvaćen`;
    case "timeout":
      return `${actor} je zakasnio`;
    case "skip":
      return `${actor} je preskočio potez`;
    case "ai_decision":
      return `${event.algorithm} je izabrao potez`;
    default:
      return event.type.replaceAll("_", " ");
  }
}

export default function EventFeed({ state }) {
  const events = state?.last_events || [];

  return (
    <section className="event-feed">
      <div className="panel-title"><ListTree size={16} /> Dnevnik poteza</div>
      <div className="event-list">
        {events.length === 0 && <span className="empty-log">Dnevnik poteza će se popuniti tokom partije.</span>}
        {events.slice(-6).map((event, index) => (
          <div className="event-row" key={`${event.type}-${index}`}>
            <span className="event-dot" />
            <span>{formatEvent(event, state)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

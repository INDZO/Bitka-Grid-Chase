import PixelSprite from "./PixelSprite.jsx";

function keyOf(pos) {
  return `${pos[0]}:${pos[1]}`;
}

export default function Board({
  state,
  teleportMode,
  validMoveTargets = new Set(),
  validTeleportTargets = new Set(),
  inputDisabled = false,
  statusMessage = "",
  currentTurn,
  myEntityId,
  debugOverlay,
  onCellClick,
}) {
  if (!state?.board) {
    return <div className="board-placeholder">Soba čeka igrače...</div>;
  }

  const { board, entities } = state;
  const walls = new Set(board.walls.map(keyOf));
  const vines = new Set(board.vines.map(keyOf));
  const memories = new Map(board.memories.filter((memory) => !memory.collected).map((memory) => [keyOf(memory.pos), memory]));
  const portalKey = keyOf(board.portal);
  const debugConsidered = new Set((debugOverlay?.considered_cells || []).map(keyOf));
  const debugPath = new Set((debugOverlay?.path || []).map(keyOf));
  const debugSelected = debugOverlay?.selected_target ? keyOf(debugOverlay.selected_target) : "";
  const entityByCell = new Map();

  Object.entries(entities).forEach(([id, entity]) => {
    if (entity.escaped || entity.active === false) return;
    entityByCell.set(keyOf(entity.pos), { id, entity });
  });

  const cells = [];
  for (let row = 0; row < board.size; row += 1) {
    for (let col = 0; col < board.size; col += 1) {
      const key = `${row}:${col}`;
      const entity = entityByCell.get(key);
      const classNames = ["cell"];
      if (walls.has(key)) classNames.push("wall");
      if (vines.has(key)) classNames.push("vines");
      if (portalKey === key) classNames.push("portal");
      if (memories.has(key)) classNames.push("memory");
      if (entity?.entity.kind === "hero") classNames.push("occupied-hero");
      if (entity?.entity.kind === "monster") classNames.push("occupied-monster");
      if (entity?.id === currentTurn) classNames.push("current-actor");
      if (entity?.id === myEntityId) classNames.push("my-actor");
      if (debugConsidered.has(key)) classNames.push("ai-considered");
      if (debugPath.has(key)) classNames.push("ai-path");
      if (debugSelected === key) classNames.push("ai-selected");
      if (teleportMode) {
        classNames.push("targeting");
        classNames.push(validTeleportTargets.has(key) ? "valid-target" : "invalid-target");
      } else if (validMoveTargets.has(key)) {
        classNames.push("valid-move-target");
      }

      cells.push(
        <button
          className={classNames.join(" ")}
          key={key}
          type="button"
          disabled={inputDisabled || (teleportMode && !validTeleportTargets.has(key))}
          data-cell={key}
          onClick={() => onCellClick?.([row, col])}
          aria-label={`Polje ${row + 1}, ${col + 1}`}
        >
          <span className="tile-noise" />
          <span className="tile-gate" />
          <span className="ai-debug-mark" />
          {walls.has(key) && <PixelSprite type="wall" label="Wall of Darkness" />}
          {!walls.has(key) && vines.has(key) && <PixelSprite type="vines" label="Vines" />}
          {memories.has(key) && <PixelSprite type="memory" label="Sećanje" />}
          {portalKey === key && <PixelSprite type="portal" label="Portal" />}
          {entity?.entity.kind === "hero" && <PixelSprite type="hero" skin={entity.entity.skin} label={entity.entity.skin} />}
          {entity?.entity.kind === "monster" && <PixelSprite type="monster" variant={entity.entity.name} label={entity.entity.name} />}
        </button>
      );
    }
  }

  return (
    <div className={inputDisabled ? "board-shell input-locked" : "board-shell"}>
      <div className="board" style={{ gridTemplateColumns: `repeat(${board.size}, minmax(42px, 1fr))` }}>
        {cells}
      </div>
      {statusMessage && <div className="board-status-pill">{statusMessage}</div>}
    </div>
  );
}

function R({ x, y, w = 1, h = 1, fill }) {
  return <rect x={x} y={y} width={w} height={h} fill={fill} />;
}

function Svg({ className, label, children }) {
  return (
    <svg
      className={className}
      viewBox="0 0 16 16"
      role="img"
      aria-label={label}
      shapeRendering="crispEdges"
      focusable="false"
    >
      {children}
    </svg>
  );
}

const markerColors = { Scout: "#64d8ef", Builder: "#ffd166", Ranger: "#7ee394", Runner: "#cba6ff", Guide: "#ef94ae", Pilot: "#f5a26b" };

function HeroSprite({ skin = "Scout", label }) {
  const fill = markerColors[skin] || markerColors.Scout;
  return (
    <Svg className="sprite sprite-hero" label={label || skin}>
      <R x="3" y="3" w="10" h="10" fill={fill} />
      <R x="6" y="6" w="4" h="4" fill="#182434" />
      <R x="7" y="1" w="2" h="3" fill={fill} />
    </Svg>
  );
}

function MonsterSprite({ variant = "Sentinel", label }) {
  return (
    <Svg className="sprite sprite-monster" label={label || variant}>
      <R x="3" y="6" w="10" h="4" fill="#ef746b" />
      <R x="6" y="3" w="4" h="10" fill="#ef746b" />
      <R x="7" y="7" w="2" h="2" fill="#182434" />
    </Svg>
  );
}

function MemorySprite({ label }) {
  return (
    <Svg className="sprite sprite-memory" label={label || "Sećanje"}>
      <R x="7" y="1" w="2" h="2" fill="#fff0a8" />
      <R x="5" y="3" w="6" h="2" fill="#ffd166" />
      <R x="3" y="5" w="10" h="6" fill="#ffd166" />
      <R x="5" y="7" w="6" h="2" fill="#fff0a8" />
      <R x="5" y="11" w="6" h="2" fill="#9b6a12" />
      <R x="7" y="13" w="2" h="2" fill="#5d3a00" />
    </Svg>
  );
}

function PortalSprite({ label }) {
  return (
    <Svg className="sprite sprite-portal" label={label || "Portal"}>
      <R x="5" y="1" w="6" h="1" fill="#62dbff" />
      <R x="3" y="2" w="10" h="2" fill="#2aa8d5" />
      <R x="2" y="4" w="12" h="8" fill="#62dbff" />
      <R x="4" y="5" w="8" h="6" fill="#150927" />
      <R x="6" y="6" w="4" h="4" fill="#8f5cff" />
      <R x="7" y="7" w="2" h="2" fill="#fff7f5" />
      <R x="3" y="12" w="10" h="2" fill="#2aa8d5" />
      <R x="5" y="14" w="6" h="1" fill="#62dbff" />
    </Svg>
  );
}

function WallSprite({ label }) {
  return (
    <Svg className="sprite sprite-wall" label={label || "Wall of Darkness"}>
      <R x="0" y="0" w="16" h="16" fill="#070507" />
      <R x="2" y="0" w="2" h="16" fill="#24131a" />
      <R x="7" y="0" w="2" h="16" fill="#3a121a" />
      <R x="12" y="0" w="2" h="16" fill="#24131a" />
      <R x="0" y="4" w="16" h="1" fill="#12090d" />
      <R x="0" y="10" w="16" h="1" fill="#12090d" />
    </Svg>
  );
}

function VinesSprite({ label }) {
  return (
    <Svg className="sprite sprite-vines" label={label || "Vines"}>
      <R x="0" y="0" w="16" h="16" fill="transparent" />
      <R x="0" y="13" w="3" h="3" fill="#14532d" />
      <R x="3" y="10" w="3" h="3" fill="#166534" />
      <R x="6" y="7" w="3" h="3" fill="#15803d" />
      <R x="9" y="4" w="3" h="3" fill="#16a34a" />
      <R x="12" y="1" w="3" h="3" fill="#34d399" />
      <R x="1" y="3" w="2" h="2" fill="#34d399" />
      <R x="4" y="5" w="2" h="2" fill="#16a34a" />
      <R x="11" y="11" w="2" h="2" fill="#34d399" />
    </Svg>
  );
}

function ResultSprite({ type, label }) {
  const victory = type === "victory";
  return (
    <Svg className={`sprite sprite-${type}`} label={label || type}>
      <R x="2" y="2" w="12" h="12" fill={victory ? "#ffd166" : "#551018"} />
      <R x="4" y="4" w="8" h="8" fill={victory ? "#fff0a8" : "#ff4b3e"} />
      {victory ? (
        <>
          <R x="7" y="1" w="2" h="4" fill="#ffd166" />
          <R x="5" y="8" w="2" h="2" fill="#1e1418" />
          <R x="7" y="10" w="2" h="2" fill="#1e1418" />
          <R x="9" y="6" w="2" h="4" fill="#1e1418" />
        </>
      ) : (
        <>
          <R x="5" y="5" w="2" h="2" fill="#080506" />
          <R x="10" y="5" w="2" h="2" fill="#080506" />
          <R x="6" y="10" w="5" h="1" fill="#080506" />
        </>
      )}
    </Svg>
  );
}

export function PixelSpriteAsset({ type, skin, label, variant }) {
  if (type === "hero") return <HeroSprite skin={skin} label={label} />;
  if (type === "monster") return <MonsterSprite variant={variant} label={label} />;
  if (type === "memory") return <MemorySprite label={label} />;
  if (type === "portal") return <PortalSprite label={label} />;
  if (type === "wall") return <WallSprite label={label} />;
  if (type === "vines") return <VinesSprite label={label} />;
  if (type === "victory" || type === "defeat") return <ResultSprite type={type} label={label} />;
  return <MemorySprite label={label || type} />;
}

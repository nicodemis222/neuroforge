import React, { useMemo, useState } from "react";
import { color, space, SEVERITY_COLOR } from "../styles/tokens";
import type { Intervention } from "../lib/api";

/**
 * Force-spread label placement: greedy collision avoidance against
 * already-placed labels. Better than D3-force for our small N (~42).
 */
function placeLabels(points: { x: number; y: number; w: number; h: number }[]) {
  const placed: { x: number; y: number; w: number; h: number }[] = [];
  return points.map(p => {
    const offsets = [
      [12, 0], [-12, 0], [0, -12], [0, 12],
      [12, -12], [-12, -12], [12, 12], [-12, 12],
      [22, 0], [-22, 0], [0, -22], [0, 22],
    ];
    for (const [dx, dy] of offsets) {
      const lx = p.x + dx;
      const ly = p.y + dy;
      const collides = placed.some(o =>
        Math.abs(lx - o.x) < (p.w + o.w) / 2 &&
        Math.abs(ly - o.y) < (p.h + o.h) / 2);
      if (!collides) {
        const placement = { x: lx, y: ly, w: p.w, h: p.h };
        placed.push(placement);
        return { lx, ly, anchor: dx >= 0 ? "start" : "end" };
      }
    }
    placed.push({ x: p.x + 12, y: p.y, w: p.w, h: p.h });
    return { lx: p.x + 12, ly: p.y, anchor: "start" };
  });
}

export const Scatter: React.FC<{
  items: Intervention[];
  selected: string | null;
  onSelect: (key: string) => void;
}> = ({ items, selected, onSelect }) => {
  const [hover, setHover] = useState<string | null>(null);
  const W = 720, H = 460, P = 56;

  const seeded = items.filter(i => i.mean_quality != null && i.mean_plausibility != null);

  const points = useMemo(() => seeded.map(i => ({
    it: i,
    cx: P + (i.mean_quality ?? 0) * (W - 2 * P),
    cy: (H - P) - (i.mean_plausibility ?? 0) * (H - 2 * P),
  })), [seeded]);

  const labelPositions = useMemo(() =>
    placeLabels(points.map(p => ({
      x: p.cx, y: p.cy,
      w: Math.max(60, p.it.name.length * 6),
      h: 14,
    }))), [points]);

  return (
    <div style={{
      background: color.bg1, border: `1px solid ${color.border}`,
      borderRadius: 6, padding: space.md, height: "100%",
      display: "grid", gridTemplateRows: "auto 1fr auto",
    }}>
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        marginBottom: space.sm,
      }}>
        <div style={{ color: color.text, fontSize: 12, fontWeight: 500 }}>
          evidence map
        </div>
        <div style={{ color: color.textFaint, fontSize: 10 }}>
          {seeded.length} seeded · {items.length - seeded.length} pending
        </div>
      </div>

      {seeded.length === 0 ? (
        <EmptyState />
      ) : (
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "100%" }}>
          {/* quadrant guides */}
          <line x1={P} y1={(P + H - P) / 2} x2={W - P} y2={(P + H - P) / 2}
                stroke={color.border} strokeDasharray="2 4" />
          <line x1={(P + W - P) / 2} y1={P} x2={(P + W - P) / 2} y2={H - P}
                stroke={color.border} strokeDasharray="2 4" />

          {/* axes */}
          <line x1={P} y1={H - P} x2={W - P} y2={H - P} stroke={color.borderStrong} />
          <line x1={P} y1={P} x2={P} y2={H - P} stroke={color.borderStrong} />

          {/* axis ticks */}
          {[0, 0.25, 0.5, 0.75, 1].map(t => (
            <g key={t}>
              <line x1={P + t * (W - 2 * P)} y1={H - P} x2={P + t * (W - 2 * P)} y2={H - P + 4} stroke={color.borderStrong} />
              <text x={P + t * (W - 2 * P)} y={H - P + 14} fill={color.textFaint} fontSize={9} textAnchor="middle">{t}</text>
              <line x1={P} y1={(H - P) - t * (H - 2 * P)} x2={P - 4} y2={(H - P) - t * (H - 2 * P)} stroke={color.borderStrong} />
              <text x={P - 7} y={(H - P) - t * (H - 2 * P) + 3} fill={color.textFaint} fontSize={9} textAnchor="end">{t}</text>
            </g>
          ))}

          {/* axis labels */}
          <text x={W / 2} y={H - 12} fill={color.textDim} fontSize={11} textAnchor="middle">
            evidence quality →
          </text>
          <text x={14} y={H / 2} fill={color.textDim} fontSize={11} textAnchor="middle"
                transform={`rotate(-90 14 ${H / 2})`}>
            mechanistic plausibility →
          </text>

          {/* quadrant titles */}
          <text x={W - P - 6} y={P + 12} fill={color.accent} fontSize={9} textAnchor="end" opacity={0.7}>
            HIGH Q + HIGH P
          </text>
          <text x={P + 6} y={P + 12} fill={color.textFaint} fontSize={9} textAnchor="start" opacity={0.7}>
            LOW Q + HIGH P
          </text>

          {/* points */}
          {points.map((p, i) => {
            const isSel = selected === p.it.key;
            const isHover = hover === p.it.key;
            const r = isSel ? 8 : isHover ? 6 : 4;
            const c = SEVERITY_COLOR[p.it.safety_overall] || color.textDim;
            const lp = labelPositions[i];
            return (
              <g key={p.it.key} style={{ cursor: "pointer" }}
                 onClick={() => onSelect(p.it.key)}
                 onMouseEnter={() => setHover(p.it.key)}
                 onMouseLeave={() => setHover(null)}>
                {(isSel || isHover) && (
                  <line x1={p.cx} y1={p.cy} x2={lp.lx} y2={lp.ly}
                        stroke={c} strokeWidth={0.5} opacity={0.4} />
                )}
                <circle cx={p.cx} cy={p.cy} r={r} fill={c}
                        stroke={isSel ? "#fff" : "transparent"} strokeWidth={1.5} />
                <text x={lp.lx} y={lp.ly + 4}
                      fill={isSel || isHover ? color.text : color.textDim}
                      fontSize={isSel ? 11 : 10}
                      textAnchor={lp.anchor as any}
                      style={{ pointerEvents: "none" }}>
                  {p.it.name}
                </text>
              </g>
            );
          })}
        </svg>
      )}

      <Legend />
    </div>
  );
};

const Legend: React.FC = () => (
  <div style={{
    display: "flex", gap: space.lg, marginTop: space.sm,
    fontSize: 10, color: color.textFaint, justifyContent: "center", flexWrap: "wrap",
  }}>
    {[
      { c: SEVERITY_COLOR.ok, l: "ok" },
      { c: SEVERITY_COLOR.caution, l: "caution" },
      { c: SEVERITY_COLOR.warn, l: "warn" },
      { c: SEVERITY_COLOR.hard_block, l: "hard-block" },
    ].map(x => (
      <span key={x.l} style={{ display: "flex", alignItems: "center", gap: 4 }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: x.c }} />
        {x.l}
      </span>
    ))}
  </div>
);

const EmptyState: React.FC = () => (
  <div style={{
    display: "grid", placeItems: "center", color: color.textFaint, fontSize: 12,
    border: `1px dashed ${color.border}`, borderRadius: 4,
  }}>
    <div style={{ textAlign: "center", padding: space.xl }}>
      no evidence yet — pick an intervention from the sidebar and click<br />
      <strong style={{ color: color.accent }}>↻ refresh</strong> to populate, or run<br />
      <code style={{ background: color.bg2, padding: "2px 6px", borderRadius: 3 }}>./scripts/once.sh clemastine</code>
    </div>
  </div>
);

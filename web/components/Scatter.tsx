import React, { useMemo, useRef, useState, useEffect } from "react";
import { color, space, radius, SEVERITY_COLOR, TIER_COLOR } from "../styles/tokens";
import { PanelHeader } from "./PanelHeader";
import type { Intervention } from "../lib/api";

/**
 * Scatter — evidence quality (x) × mechanistic plausibility (y).
 *
 * - Receives the *filtered* item list from the parent so sidebar filters
 *   apply to the map identically.
 * - Highlights the currently-selected intervention with a pulse ring +
 *   leader to its label even when not hovered.
 * - Stack handling: points within a small radius are fanned around a
 *   jitter circle so each gets a discrete anchor.
 * - Greedy collision-avoidance for label placement, falling back to
 *   leader-only when no clear slot exists.
 */

type Pt = { it: Intervention; cx: number; cy: number };

const CATEGORY_SHAPE: Record<string, string> = {
  drug: "circle",
  biologic: "diamond",
  supplement: "square",
  behavioral: "triangle",
  device: "hexagon",
  holistic: "star",
};

function spreadStacks(pts: Pt[]): Pt[] {
  const groups: Pt[][] = [];
  const visited = new Set<number>();
  for (let i = 0; i < pts.length; i++) {
    if (visited.has(i)) continue;
    const group = [pts[i]]; visited.add(i);
    for (let j = i + 1; j < pts.length; j++) {
      if (visited.has(j)) continue;
      if (Math.hypot(pts[i].cx - pts[j].cx, pts[i].cy - pts[j].cy) < 12) {
        group.push(pts[j]); visited.add(j);
      }
    }
    groups.push(group);
  }
  const out: Pt[] = [];
  for (const g of groups) {
    if (g.length === 1) { out.push(g[0]); continue; }
    // Fan-out radius scales with stack size so larger clumps get more space.
    const r = Math.max(18, 10 + g.length * 5);
    g.forEach((p, k) => {
      // Bias the fan toward open quadrants — when the stack is in the
      // top-right corner, fan downward + leftward to stay inside the plot.
      const baseAngle = -Math.PI / 4; // fan toward the lower-left when in top-right
      const angle = baseAngle + (2 * Math.PI * k) / g.length;
      out.push({ ...p, cx: p.cx + Math.cos(angle) * r, cy: p.cy + Math.sin(angle) * r });
    });
  }
  return out;
}

function placeLabels(points: { x: number; y: number; w: number; h: number }[]) {
  const placed: { x: number; y: number; w: number; h: number }[] = [];
  return points.map(p => {
    const offsets = [
      [16, 0], [-16, 0], [0, -18], [0, 18],
      [18, -14], [-18, -14], [18, 14], [-18, 14],
      [28, 0], [-28, 0], [0, -28], [0, 28],
      [30, -22], [-30, -22], [30, 22], [-30, 22],
      [40, 0], [-40, 0], [0, -40], [0, 40],
    ];
    for (const [dx, dy] of offsets) {
      const lx = p.x + dx;
      const ly = p.y + dy;
      const collides = placed.some(o =>
        Math.abs(lx - o.x) < (p.w + o.w) / 2 + 2 &&
        Math.abs(ly - o.y) < (p.h + o.h) / 2 + 2);
      if (!collides) {
        placed.push({ x: lx, y: ly, w: p.w, h: p.h });
        return { lx, ly, anchor: dx >= 0 ? "start" : "end", placed: true };
      }
    }
    placed.push({ x: p.x + 16, y: p.y, w: p.w, h: p.h });
    return { lx: p.x + 16, ly: p.y, anchor: "start", placed: false };
  });
}

const renderShape = (
  cx: number, cy: number, r: number, category: string,
  fill: string, stroke: string, strokeWidth: number,
  onClick: (e: React.MouseEvent) => void, onEnter: () => void, onLeave: () => void,
) => {
  const common = { fill, stroke, strokeWidth, onClick, onMouseEnter: onEnter, onMouseLeave: onLeave, style: { cursor: "pointer" } };
  const shape = CATEGORY_SHAPE[category] || "circle";
  if (shape === "diamond") {
    const pts = `${cx},${cy - r * 1.2} ${cx + r * 1.1},${cy} ${cx},${cy + r * 1.2} ${cx - r * 1.1},${cy}`;
    return <polygon points={pts} {...common} />;
  }
  if (shape === "square") {
    return <rect x={cx - r} y={cy - r} width={r * 2} height={r * 2} {...common} />;
  }
  if (shape === "triangle") {
    const pts = `${cx},${cy - r * 1.2} ${cx + r * 1.1},${cy + r * 0.7} ${cx - r * 1.1},${cy + r * 0.7}`;
    return <polygon points={pts} {...common} />;
  }
  if (shape === "hexagon") {
    const a = r * 1.1;
    const pts = [0, 60, 120, 180, 240, 300]
      .map(d => {
        const rad = (d * Math.PI) / 180;
        return `${cx + Math.cos(rad) * a},${cy + Math.sin(rad) * a}`;
      }).join(" ");
    return <polygon points={pts} {...common} />;
  }
  if (shape === "star") {
    const outer = r * 1.3, inner = r * 0.55;
    const pts: string[] = [];
    for (let i = 0; i < 10; i++) {
      const rad = (Math.PI / 5) * i - Math.PI / 2;
      const rr = i % 2 === 0 ? outer : inner;
      pts.push(`${cx + Math.cos(rad) * rr},${cy + Math.sin(rad) * rr}`);
    }
    return <polygon points={pts.join(" ")} {...common} />;
  }
  return <circle cx={cx} cy={cy} r={r} {...common} />;
};

export const Scatter: React.FC<{
  items: Intervention[];          // already-filtered by parent
  totalItems: number;             // unfiltered count, for status text
  selected: string | null;
  onSelect: (key: string) => void;
}> = ({ items, totalItems, selected, onSelect }) => {
  const [hover, setHover] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ w: 1000, h: 600 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      for (const e of entries) {
        const { width, height } = e.contentRect;
        setSize({ w: Math.max(400, width), h: Math.max(300, height) });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const W = size.w, H = size.h, P = 70;
  const seeded = items.filter(i => i.mean_quality != null && i.mean_plausibility != null);
  const pending = items.length - seeded.length;

  const pointsRaw: Pt[] = useMemo(() => seeded.map(i => ({
    it: i,
    cx: P + (i.mean_quality ?? 0) * (W - 2 * P),
    cy: (H - P) - (i.mean_plausibility ?? 0) * (H - 2 * P),
  })), [seeded, W, H]);

  const points = useMemo(() => spreadStacks(pointsRaw), [pointsRaw]);

  const labelPositions = useMemo(() =>
    placeLabels(points.map(p => ({
      x: p.cx, y: p.cy,
      w: Math.max(80, p.it.name.length * 7),
      h: 16,
    }))), [points]);

  return (
    <div style={{
      background: color.bg1, border: `1px solid ${color.border}`,
      borderRadius: radius.md, height: "100%",
      display: "grid", gridTemplateRows: "auto 1fr auto", overflow: "hidden",
    }}>
      <PanelHeader
        title="Evidence map"
        subtitle="top-right = read first · color = safety · shape = category"
        right={
          <span style={{ color: color.textFaint, fontSize: 11 }}>
            {seeded.length} seeded · {pending} pending · {items.length}/{totalItems} after filters
          </span>
        }
      />

      <div ref={containerRef} style={{ position: "relative", overflow: "hidden" }}>
        {seeded.length === 0 ? (
          <EmptyState filtered={items.length < totalItems} />
        ) : (
          <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}
               style={{ display: "block", background: color.bg1 }}>
            {/* Quadrant tints */}
            <rect x={(P + W - P) / 2} y={P} width={(W - 2 * P) / 2} height={(H - 2 * P) / 2}
                  fill={color.accent} opacity={0.04} />

            {/* gridlines */}
            {[0.25, 0.5, 0.75].map(t => (
              <g key={t}>
                <line x1={P + t * (W - 2 * P)} y1={P} x2={P + t * (W - 2 * P)} y2={H - P}
                      stroke={color.border} strokeDasharray="2 6" opacity={0.6} />
                <line x1={P} y1={(H - P) - t * (H - 2 * P)} x2={W - P} y2={(H - P) - t * (H - 2 * P)}
                      stroke={color.border} strokeDasharray="2 6" opacity={0.6} />
              </g>
            ))}

            {/* axes */}
            <line x1={P} y1={H - P} x2={W - P} y2={H - P} stroke={color.borderStrong} strokeWidth={1.5} />
            <line x1={P} y1={P} x2={P} y2={H - P} stroke={color.borderStrong} strokeWidth={1.5} />

            {/* axis ticks */}
            {[0, 0.25, 0.5, 0.75, 1].map(t => (
              <g key={t}>
                <line x1={P + t * (W - 2 * P)} y1={H - P} x2={P + t * (W - 2 * P)} y2={H - P + 6} stroke={color.borderStrong} />
                <text x={P + t * (W - 2 * P)} y={H - P + 22} fill={color.textDim} fontSize={12} textAnchor="middle">{t}</text>
                <line x1={P} y1={(H - P) - t * (H - 2 * P)} x2={P - 6} y2={(H - P) - t * (H - 2 * P)} stroke={color.borderStrong} />
                <text x={P - 12} y={(H - P) - t * (H - 2 * P) + 4} fill={color.textDim} fontSize={12} textAnchor="end">{t}</text>
              </g>
            ))}

            {/* axis labels — kept outside the data area */}
            <text x={W / 2} y={H - 18} fill={color.text} fontSize={13} textAnchor="middle" fontWeight={500}>
              evidence quality →
            </text>
            <text x={20} y={H / 2} fill={color.text} fontSize={13} textAnchor="middle" fontWeight={500}
                  transform={`rotate(-90 20 ${H / 2})`}>
              mechanistic plausibility →
            </text>

            {/* points */}
            {points.map((p, i) => {
              const isSel = selected === p.it.key;
              const isHover = hover === p.it.key;
              const r = isSel ? 10 : isHover ? 9 : 7;
              const c = SEVERITY_COLOR[p.it.safety_overall] || color.textDim;
              const lp = labelPositions[i];
              return (
                <g key={p.it.key}>
                  {isSel && (
                    <circle cx={p.cx} cy={p.cy} r={r + 7} fill="none"
                            stroke={c} strokeWidth={1} opacity={0.4}>
                      <animate attributeName="r" values={`${r + 5};${r + 12};${r + 5}`} dur="2s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.4;0.1;0.4" dur="2s" repeatCount="indefinite" />
                    </circle>
                  )}
                  {(isSel || isHover) && (
                    <line x1={p.cx} y1={p.cy} x2={lp.lx} y2={lp.ly}
                          stroke={c} strokeWidth={0.8} opacity={0.6} />
                  )}
                  {renderShape(p.cx, p.cy, r, p.it.category, c,
                    isSel ? "#fff" : isHover ? color.text : "transparent",
                    isSel ? 2 : 1.5,
                    () => onSelect(p.it.key),
                    () => setHover(p.it.key),
                    () => setHover(null))}
                  <text x={lp.lx + (lp.anchor === "start" ? 4 : -4)}
                        y={lp.ly + 5}
                        fill={isSel || isHover ? color.text : color.textDim}
                        fontSize={isSel ? 13 : 12}
                        fontWeight={isSel ? 600 : 400}
                        textAnchor={lp.anchor as any}
                        style={{ pointerEvents: "none" }}>
                    {p.it.name}
                  </text>
                </g>
              );
            })}

            {/* hover detail card */}
            {hover && (() => {
              const p = points.find(x => x.it.key === hover);
              if (!p) return null;
              const x = Math.min(W - 240, Math.max(10, p.cx + 16));
              const y = Math.min(H - 120, Math.max(10, p.cy - 60));
              const c = SEVERITY_COLOR[p.it.safety_overall] || color.textDim;
              return (
                <g style={{ pointerEvents: "none" }}>
                  <rect x={x} y={y} width={230} height={100} rx={4}
                        fill={color.bg2} stroke={c} strokeWidth={1.5} opacity={0.97} />
                  <text x={x + 10} y={y + 18} fill={color.text} fontSize={12} fontWeight={600}>
                    {p.it.name.length > 28 ? p.it.name.slice(0, 28) + "…" : p.it.name}
                  </text>
                  <text x={x + 10} y={y + 36} fill={color.textDim} fontSize={10}>
                    {p.it.category} · tier {p.it.expected_tier} · seizure: {p.it.seizure_risk}
                  </text>
                  <text x={x + 10} y={y + 56} fill={color.textDim} fontSize={11}>
                    n={p.it.n_evidence} · q={p.it.mean_quality?.toFixed(2)} · p={p.it.mean_plausibility?.toFixed(2)}
                  </text>
                  <text x={x + 10} y={y + 74} fill={c} fontSize={10} fontWeight={600}>
                    {p.it.safety_overall.replace("_", " ").toUpperCase()}
                  </text>
                  <text x={x + 10} y={y + 90} fill={color.textFaint} fontSize={9}>
                    click for full briefing
                  </text>
                </g>
              );
            })()}
          </svg>
        )}
      </div>

      <Legend />
    </div>
  );
};

const Legend: React.FC = () => (
  <div style={{
    display: "flex", gap: space.lg, padding: `${space.sm}px ${space.md}px`,
    fontSize: 11, color: color.textFaint, alignItems: "center", flexWrap: "wrap",
    borderTop: `1px solid ${color.border}`, justifyContent: "space-between",
  }}>
    <div style={{ display: "flex", gap: space.md, alignItems: "center" }}>
      <span style={{ color: color.textDim }}>safety:</span>
      {[
        { c: SEVERITY_COLOR.ok, l: "ok" },
        { c: SEVERITY_COLOR.caution, l: "caution" },
        { c: SEVERITY_COLOR.warn, l: "warn" },
        { c: SEVERITY_COLOR.hard_block, l: "hard-block" },
      ].map(x => (
        <span key={x.l} style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 10, height: 10, borderRadius: "50%", background: x.c }} />
          {x.l}
        </span>
      ))}
    </div>
    <div style={{ display: "flex", gap: space.md, alignItems: "center" }}>
      <span style={{ color: color.textDim }}>shape = category:</span>
      <ShapeKey shape="circle" label="drug" />
      <ShapeKey shape="diamond" label="biologic" />
      <ShapeKey shape="square" label="supplement" />
      <ShapeKey shape="triangle" label="behavioral" />
      <ShapeKey shape="hexagon" label="device" />
      <ShapeKey shape="star" label="holistic" />
    </div>
  </div>
);

const ShapeKey: React.FC<{ shape: string; label: string }> = ({ shape, label }) => (
  <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
    <svg width={14} height={14} viewBox="-7 -7 14 14">
      {renderShape(0, 0, 5, label, color.textDim, "transparent", 0,
        () => {}, () => {}, () => {})}
    </svg>
    {label}
  </span>
);

const EmptyState: React.FC<{ filtered: boolean }> = ({ filtered }) => (
  <div style={{
    display: "grid", placeItems: "center", height: "100%", color: color.textFaint, fontSize: 13,
  }}>
    <div style={{ textAlign: "center", padding: space.xl, maxWidth: 480 }}>
      {filtered
        ? <>your filters narrowed everything off the map.<br/>clear filters in the sidebar to see results.</>
        : <>no evidence yet — pick an intervention from the catalog and click<br/>
            <strong style={{ color: color.accent }}>↻ refresh evidence</strong> to populate, or run<br/>
            <code style={{ background: color.bg2, padding: "3px 8px", borderRadius: 3, marginTop: space.sm, display: "inline-block" }}>
              ./scripts/once.sh clemastine
            </code></>}
    </div>
  </div>
);

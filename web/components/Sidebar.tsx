import React, { useMemo, useState } from "react";
import { color, space, radius, SEVERITY_COLOR, TIER_COLOR } from "../styles/tokens";
import type { Intervention } from "../lib/api";

const CATEGORIES = ["drug", "biologic", "supplement", "behavioral", "device", "holistic"];
const TIERS = ["T1", "T2", "T3", "T4", "T5"];
const SAFETY = ["ok", "caution", "warn", "hard_block"];

type Filters = {
  q: string;
  category: Set<string>;
  tier: Set<string>;
  safety: Set<string>;
  hideEmpty: boolean;
};

const defaultFilters = (): Filters => ({
  q: "", category: new Set(), tier: new Set(), safety: new Set(), hideEmpty: false,
});

const ChipToggle: React.FC<{
  active: boolean; onClick: () => void; tone?: string; children: React.ReactNode;
}> = ({ active, onClick, tone, children }) => (
  <button onClick={onClick} style={{
    padding: "3px 8px", borderRadius: radius.sm, fontSize: 10,
    background: active ? (tone || color.accentBg) : color.bg2,
    color: active ? "#fff" : color.textDim,
    border: `1px solid ${active ? (tone || color.accent) : color.border}`,
    cursor: "pointer", fontFamily: "inherit",
  }}>{children}</button>
);

export const Sidebar: React.FC<{
  items: Intervention[];
  selected: string | null;
  onSelect: (key: string) => void;
}> = ({ items, selected, onSelect }) => {
  const [f, setF] = useState<Filters>(defaultFilters());

  const filtered = useMemo(() => {
    const q = f.q.trim().toLowerCase();
    return items.filter(it => {
      if (q && !it.name.toLowerCase().includes(q) && !it.targets.join(" ").toLowerCase().includes(q)) return false;
      if (f.category.size && !f.category.has(it.category)) return false;
      if (f.tier.size && !f.tier.has(it.expected_tier)) return false;
      if (f.safety.size && !f.safety.has(it.safety_overall)) return false;
      if (f.hideEmpty && it.n_evidence === 0) return false;
      return true;
    });
  }, [items, f]);

  const toggle = (key: keyof Filters, val: string) => setF(prev => {
    const next = new Set(prev[key] as Set<string>);
    next.has(val) ? next.delete(val) : next.add(val);
    return { ...prev, [key]: next };
  });

  const reset = () => setF(defaultFilters());
  const filterActive = f.q || f.category.size || f.tier.size || f.safety.size || f.hideEmpty;

  return (
    <aside style={{
      width: 360, background: color.bg1, borderRight: `1px solid ${color.border}`,
      display: "grid", gridTemplateRows: "auto auto 1fr", overflow: "hidden",
    }}>
      <div style={{ padding: space.md, borderBottom: `1px solid ${color.border}` }}>
        <input
          value={f.q}
          onChange={e => setF(p => ({ ...p, q: e.target.value }))}
          placeholder="search interventions or targets…"
          style={{
            width: "100%", padding: `${space.sm}px ${space.md}px`,
            background: color.bg0, border: `1px solid ${color.border}`,
            borderRadius: radius.sm, color: color.text, outline: "none",
            fontSize: 12,
          }}
        />
      </div>

      <div style={{ padding: space.md, borderBottom: `1px solid ${color.border}`, display: "grid", gap: space.sm }}>
        <FilterRow label="category">
          {CATEGORIES.map(c => (
            <ChipToggle key={c} active={f.category.has(c)} onClick={() => toggle("category", c)}>
              {c}
            </ChipToggle>
          ))}
        </FilterRow>
        <FilterRow label="tier">
          {TIERS.map(t => (
            <ChipToggle key={t} active={f.tier.has(t)} onClick={() => toggle("tier", t)} tone={TIER_COLOR[t]}>
              {t}
            </ChipToggle>
          ))}
        </FilterRow>
        <FilterRow label="safety">
          {SAFETY.map(s => (
            <ChipToggle key={s} active={f.safety.has(s)} onClick={() => toggle("safety", s)} tone={SEVERITY_COLOR[s]}>
              {s.replace("_", " ")}
            </ChipToggle>
          ))}
        </FilterRow>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
          <ChipToggle active={f.hideEmpty} onClick={() => setF(p => ({ ...p, hideEmpty: !p.hideEmpty }))}>
            hide n=0
          </ChipToggle>
          <span style={{ color: color.textFaint, fontSize: 10 }}>
            {filtered.length} of {items.length}
            {filterActive && <button onClick={reset} style={{
              background: "transparent", border: "none", color: color.accent,
              cursor: "pointer", marginLeft: space.sm, fontSize: 10,
            }}>reset</button>}
          </span>
        </div>
      </div>

      <div style={{ overflowY: "auto", padding: space.sm }}>
        {filtered.length === 0 && (
          <div style={{ color: color.textFaint, padding: space.lg, fontSize: 12, textAlign: "center" }}>
            no matches
          </div>
        )}
        {filtered.map(it => <InterventionCard key={it.key} it={it} selected={selected === it.key} onSelect={onSelect} />)}
      </div>
    </aside>
  );
};

const FilterRow: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div style={{ display: "grid", gridTemplateColumns: "60px 1fr", alignItems: "center", gap: space.sm }}>
    <span style={{ color: color.textFaint, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</span>
    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>{children}</div>
  </div>
);

const InterventionCard: React.FC<{
  it: Intervention; selected: boolean; onSelect: (k: string) => void;
}> = ({ it, selected, onSelect }) => {
  const sevColor = SEVERITY_COLOR[it.safety_overall] || color.textDim;
  const tierColor = TIER_COLOR[it.expected_tier] || color.textDim;
  const q = it.mean_quality, p = it.mean_plausibility;

  return (
    <button onClick={() => onSelect(it.key)} style={{
      width: "100%", textAlign: "left",
      background: selected ? color.bg3 : color.bg1,
      border: `1px solid ${selected ? color.accent : color.border}`,
      borderRadius: radius.sm, padding: space.sm, marginBottom: space.xs,
      cursor: "pointer", display: "grid",
      gridTemplateColumns: "10px 1fr auto", gap: space.sm, alignItems: "center",
    }}>
      <span style={{
        width: 8, height: 8, background: sevColor, borderRadius: "50%",
        boxShadow: `0 0 0 2px ${color.bg1}`, marginTop: 4, alignSelf: "start",
      }} />
      <div style={{ minWidth: 0 }}>
        <div style={{
          color: selected ? color.accent : color.text, fontSize: 12, fontWeight: 500,
          whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
        }}>{it.name}</div>
        <div style={{ color: color.textFaint, fontSize: 10, marginTop: 2 }}>
          {it.category} · <span style={{ color: tierColor }}>{it.expected_tier}</span> · {it.seizure_risk}
        </div>
      </div>
      <div style={{
        textAlign: "right", fontSize: 10, color: color.textDim, lineHeight: 1.3,
      }}>
        <div>n={it.n_evidence}</div>
        <div>{q != null ? `q=${q.toFixed(2)}` : "—"}</div>
        <div>{p != null ? `p=${p.toFixed(2)}` : "—"}</div>
      </div>
    </button>
  );
};

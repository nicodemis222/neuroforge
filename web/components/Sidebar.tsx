import React, { useState } from "react";
import { color, space, radius, SEVERITY_COLOR, TIER_COLOR } from "../styles/tokens";
import { PanelHeader } from "./PanelHeader";
import { api, type Intervention, type Rationale } from "../lib/api";
import type { Filters } from "../lib/filters";

const CATEGORIES = ["drug", "biologic", "supplement", "behavioral", "device", "holistic"];
const TIERS = ["T1", "T2", "T3", "T4", "T5"];
const SAFETY = ["ok", "caution", "warn", "hard_block"];

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
  items: Intervention[];                // total catalog
  filtered: Intervention[];             // post-filter list
  filters: Filters;
  toggleFilter: (k: keyof Filters, v: string) => void;
  setQ: (q: string) => void;
  setHideEmpty: (b: boolean) => void;
  resetFilters: () => void;
  isFilterActive: boolean;
  selected: string | null;
  onSelect: (key: string) => void;
}> = ({ items, filtered, filters: f, toggleFilter, setQ, setHideEmpty,
        resetFilters, isFilterActive, selected, onSelect }) => {
  return (
    <aside style={{
      width: 360, background: color.bg1, borderRight: `1px solid ${color.border}`,
      display: "grid", gridTemplateRows: "auto auto auto 1fr", overflow: "hidden",
    }}>
      <PanelHeader
        title="Catalog of candidate interventions"
        subtitle="click any row for the briefing · ⓘ for the rationale"
      />
      <div style={{ padding: space.md, borderBottom: `1px solid ${color.border}` }}>
        <input
          value={f.q}
          onChange={e => setQ(e.target.value)}
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
            <ChipToggle key={c} active={f.category.has(c)} onClick={() => toggleFilter("category", c)}>
              {c}
            </ChipToggle>
          ))}
        </FilterRow>
        <FilterRow label="tier">
          {TIERS.map(t => (
            <ChipToggle key={t} active={f.tier.has(t)} onClick={() => toggleFilter("tier", t)} tone={TIER_COLOR[t]}>
              {t}
            </ChipToggle>
          ))}
        </FilterRow>
        <FilterRow label="safety">
          {SAFETY.map(s => (
            <ChipToggle key={s} active={f.safety.has(s)} onClick={() => toggleFilter("safety", s)} tone={SEVERITY_COLOR[s]}>
              {s.replace("_", " ")}
            </ChipToggle>
          ))}
        </FilterRow>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
          <ChipToggle active={f.hideEmpty} onClick={() => setHideEmpty(!f.hideEmpty)}>
            hide n=0
          </ChipToggle>
          <span style={{ color: color.textFaint, fontSize: 10 }}>
            {filtered.length} of {items.length} · also applied to evidence map
            {isFilterActive && <button onClick={resetFilters} style={{
              background: "transparent", border: "none", color: color.accent,
              cursor: "pointer", marginLeft: space.sm, fontSize: 10, fontFamily: "inherit",
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
  const [showRationale, setShowRationale] = useState(false);
  const [rationale, setRationale] = useState<Rationale | null>(null);
  const sevColor = SEVERITY_COLOR[it.safety_overall] || color.textDim;
  const tierColor = TIER_COLOR[it.expected_tier] || color.textDim;
  const q = it.mean_quality, p = it.mean_plausibility;

  const openRationale = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowRationale(s => !s);
    if (!rationale) api.rationale(it.key).then(setRationale).catch(() => {});
  };

  return (
    <div>
      <button onClick={() => onSelect(it.key)} style={{
        width: "100%", textAlign: "left",
        background: selected ? color.bg3 : color.bg1,
        border: `1px solid ${selected ? color.accent : color.border}`,
        borderRadius: radius.sm, padding: space.sm, marginBottom: showRationale ? 0 : space.xs,
        borderBottomLeftRadius: showRationale ? 0 : radius.sm,
        borderBottomRightRadius: showRationale ? 0 : radius.sm,
        cursor: "pointer", display: "grid",
        gridTemplateColumns: "10px 1fr auto auto", gap: space.sm, alignItems: "center",
        fontFamily: "inherit",
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
        <span
          onClick={openRationale}
          title="why is this intervention a candidate?"
          style={{
            color: showRationale ? color.accent : color.textFaint,
            fontSize: 14, lineHeight: 1, cursor: "pointer",
            padding: "0 4px",
          }}>ⓘ</span>
      </button>
      {showRationale && (
        <div style={{
          background: color.bg2, border: `1px solid ${color.accent}`,
          borderTop: "none",
          borderBottomLeftRadius: radius.sm, borderBottomRightRadius: radius.sm,
          padding: space.sm, marginBottom: space.xs,
          fontSize: 11, color: color.textDim, lineHeight: 1.5,
        }}>
          {rationale ? rationale.rationale : "loading rationale…"}
        </div>
      )}
    </div>
  );
};

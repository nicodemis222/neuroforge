import React from "react";
import { color, space, font } from "../styles/tokens";
import type { PatientProfile } from "../lib/api";

type Tab = "dashboard" | "corpus" | "profile";

const Pill: React.FC<{ children: React.ReactNode; tone?: "ok" | "warn" | "dim" }> = ({ children, tone = "dim" }) => {
  const tones = {
    ok: { color: color.ok, bg: "rgba(63,169,136,0.12)", border: "rgba(63,169,136,0.3)" },
    warn: { color: color.warn, bg: "rgba(240,138,58,0.12)", border: "rgba(240,138,58,0.3)" },
    dim: { color: color.textDim, bg: color.bg2, border: color.border },
  }[tone];
  return (
    <span style={{
      padding: `${space.xs}px ${space.sm}px`, borderRadius: 999,
      background: tones.bg, color: tones.color, border: `1px solid ${tones.border}`,
      fontSize: 11, lineHeight: 1, whiteSpace: "nowrap",
    }}>{children}</span>
  );
};

const TabButton: React.FC<{ active: boolean; onClick: () => void; children: React.ReactNode }> = ({ active, onClick, children }) => (
  <button onClick={onClick} style={{
    background: active ? color.bg3 : "transparent",
    color: active ? color.accent : color.textDim,
    border: "none",
    borderBottom: `2px solid ${active ? color.accent : "transparent"}`,
    padding: `${space.sm}px ${space.lg}px`,
    cursor: "pointer", fontSize: 12, fontFamily: font.mono,
    letterSpacing: "0.05em", textTransform: "uppercase",
  }}>{children}</button>
);

export const Header: React.FC<{
  tab: Tab;
  setTab: (t: Tab) => void;
  profile: PatientProfile | null;
  totalEvidence: number;
  schedulerOn: boolean;
}> = ({ tab, setTab, profile, totalEvidence, schedulerOn }) => {
  const findingsCount = profile?.findings.filter(f => !f.label.startsWith("(example)")).length || 0;
  const isExample = profile && (profile.patient_ref === "example-patient" || findingsCount === 0);

  return (
    <header style={{
      display: "grid", gridTemplateColumns: "auto 1fr auto",
      alignItems: "center", gap: space.lg,
      padding: `${space.sm}px ${space.lg}px`,
      background: color.bg1, borderBottom: `1px solid ${color.border}`,
      flexShrink: 0,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: space.md }}>
        <span style={{ color: color.accent, fontWeight: 600, fontSize: 15, letterSpacing: "0.1em" }}>
          NEUROFORGE
        </span>
        <span style={{ color: color.textFaint, fontSize: 10 }}>v0.1</span>
      </div>

      <nav style={{ display: "flex", gap: 0, justifyContent: "center" }}>
        <TabButton active={tab === "dashboard"} onClick={() => setTab("dashboard")}>Dashboard</TabButton>
        <TabButton active={tab === "corpus"} onClick={() => setTab("corpus")}>Corpus</TabButton>
        <TabButton active={tab === "profile"} onClick={() => setTab("profile")}>Profile</TabButton>
      </nav>

      <div style={{ display: "flex", gap: space.sm, alignItems: "center", flexWrap: "wrap" }}>
        {isExample
          ? <Pill tone="warn">example profile · drop docs to anchor</Pill>
          : <Pill tone="ok">{findingsCount} finding{findingsCount === 1 ? "" : "s"} · {profile?.medications.length || 0} med{profile?.medications.length === 1 ? "" : "s"}</Pill>}
        <Pill>{totalEvidence.toLocaleString()} evidence rows</Pill>
        <Pill tone={schedulerOn ? "ok" : "dim"}>scheduler {schedulerOn ? "on" : "off"}</Pill>
      </div>
    </header>
  );
};

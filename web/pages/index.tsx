import { useEffect, useState } from "react";

type Intervention = {
  key: string; name: string; category: string;
  expected_tier: string; seizure_risk: string;
  n_evidence: number; mean_quality: number | null;
  mean_plausibility: number | null;
  safety_overall: string;
  safety_flags: { severity: string; axis: string; rationale: string }[];
};

const SEV_COLOR: Record<string, string> = {
  ok: "#3fa", caution: "#fc6", warn: "#f73", hard_block: "#e33",
};

export default function Home() {
  const [items, setItems] = useState<Intervention[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [briefing, setBriefing] = useState<string>("");

  useEffect(() => {
    fetch("/api/ontology/interventions").then(r => r.json()).then(setItems);
  }, []);

  useEffect(() => {
    if (!selected) return;
    fetch(`/api/intervention/${selected}/briefing`)
      .then(r => r.json())
      .then(d => setBriefing(d.markdown));
  }, [selected]);

  const refresh = (k: string) =>
    fetch(`/api/intervention/${k}/refresh`, { method: "POST" });

  return (
    <div style={{ display: "grid", gridTemplateColumns: "440px 1fr",
                  height: "100vh", fontFamily: "ui-monospace,Menlo,monospace",
                  background: "#0a0e14", color: "#cfe" }}>
      <aside style={{ borderRight: "1px solid #1a2330", overflow: "auto", padding: 14 }}>
        <h1 style={{ margin: 0, fontSize: 18, color: "#7fe" }}>NEUROFORGE</h1>
        <p style={{ fontSize: 11, color: "#7a8" }}>
          patient-anchored neuronal-regrowth research<br/>
          chronic L-CST · cross-cerebellar diaschisis · ?focal aware seizures
        </p>
        <div style={{ display: "grid", gap: 6, marginTop: 12 }}>
          {items.map(it => (
            <button key={it.key} onClick={() => setSelected(it.key)}
              style={{
                background: selected === it.key ? "#142030" : "#0d1420",
                border: "1px solid #1a2330", color: "#cfe", textAlign: "left",
                padding: 8, cursor: "pointer", display: "grid",
                gridTemplateColumns: "1fr auto", gap: 6,
              }}>
              <span>
                <span style={{ display: "inline-block", width: 8, height: 8,
                                background: SEV_COLOR[it.safety_overall] || "#888",
                                marginRight: 6 }}/>
                <strong>{it.name}</strong>
                <br/>
                <span style={{ fontSize: 10, color: "#7a8" }}>
                  {it.category} · {it.expected_tier} · seizure: {it.seizure_risk}
                  {" · "}n={it.n_evidence}
                </span>
              </span>
              <span style={{ fontSize: 10, color: "#7a8" }}>
                q={it.mean_quality?.toFixed(2) ?? "—"}<br/>
                p={it.mean_plausibility?.toFixed(2) ?? "—"}
              </span>
            </button>
          ))}
        </div>
      </aside>
      <main style={{ overflow: "auto", padding: 18 }}>
        <Scatter items={items} onSelect={setSelected} selected={selected}/>
        {selected && (
          <div style={{ marginTop: 18 }}>
            <button onClick={() => refresh(selected)}
              style={{ background: "#142030", color: "#7fe",
                       border: "1px solid #1a2330", padding: "6px 10px",
                       cursor: "pointer", marginBottom: 10 }}>
              ↻ refresh evidence for {selected}
            </button>
            <pre style={{ whiteSpace: "pre-wrap", background: "#0d1420",
                          padding: 14, border: "1px solid #1a2330",
                          fontSize: 12, lineHeight: 1.5 }}>
              {briefing}
            </pre>
          </div>
        )}
      </main>
    </div>
  );
}

function Scatter({ items, onSelect, selected }: {
  items: Intervention[]; onSelect: (k: string) => void; selected: string | null;
}) {
  const W = 760, H = 480, P = 40;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: W,
                                              border: "1px solid #1a2330",
                                              background: "#0d1420" }}>
      <text x={W / 2} y={20} fill="#7fe" textAnchor="middle" fontSize={12}>
        evidence quality (x) × mechanistic plausibility (y)
      </text>
      <line x1={P} y1={H - P} x2={W - P} y2={H - P} stroke="#1a2330"/>
      <line x1={P} y1={P} x2={P} y2={H - P} stroke="#1a2330"/>
      {items.filter(i => i.mean_quality != null).map(i => {
        const x = P + (i.mean_quality ?? 0) * (W - 2 * P);
        const y = (H - P) - (i.mean_plausibility ?? 0) * (H - 2 * P);
        const c = SEV_COLOR[i.safety_overall] || "#888";
        return (
          <g key={i.key} onClick={() => onSelect(i.key)} style={{ cursor: "pointer" }}>
            <circle cx={x} cy={y} r={selected === i.key ? 9 : 5}
                    fill={c} stroke={selected === i.key ? "#fff" : "none"}/>
            <text x={x + 8} y={y + 3} fontSize={9} fill="#cfe">{i.name}</text>
          </g>
        );
      })}
    </svg>
  );
}

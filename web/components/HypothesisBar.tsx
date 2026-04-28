import React, { useEffect, useState } from "react";
import { color, space, radius } from "../styles/tokens";
import { api, type Hypothesis } from "../lib/api";

const Chip: React.FC<{
  tone?: "ok" | "warn" | "info" | "block";
  children: React.ReactNode;
  title?: string;
}> = ({ tone = "info", children, title }) => {
  const palette = {
    ok: { bg: "rgba(63,169,136,0.12)", border: "rgba(63,169,136,0.4)", text: color.ok },
    warn: { bg: "rgba(245,201,90,0.12)", border: "rgba(245,201,90,0.4)", text: color.caution },
    info: { bg: color.bg2, border: color.border, text: color.text },
    block: { bg: "rgba(232,90,90,0.12)", border: "rgba(232,90,90,0.4)", text: color.block },
  }[tone];
  return (
    <span title={title} style={{
      display: "inline-block", padding: "3px 9px", borderRadius: 999,
      background: palette.bg, border: `1px solid ${palette.border}`,
      color: palette.text, fontSize: 10, lineHeight: 1.4,
      whiteSpace: "nowrap",
    }}>{children}</span>
  );
};

export const HypothesisBar: React.FC = () => {
  const [h, setH] = useState<Hypothesis | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    api.hypothesis().then(setH);
    const t = setInterval(() => api.hypothesis().then(setH), 60000);
    return () => clearInterval(t);
  }, []);

  if (!h) return null;

  return (
    <section style={{
      background: color.bg1, borderBottom: `1px solid ${color.border}`,
      padding: `${space.sm}px ${space.lg}px`, flexShrink: 0,
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: space.lg }}>
        <div style={{
          color: color.accent, fontSize: 10, fontWeight: 600,
          letterSpacing: "0.1em", textTransform: "uppercase",
          minWidth: 130, paddingTop: 2,
        }}>
          Active investigation
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            color: color.text, fontSize: 12, lineHeight: 1.5,
            marginBottom: space.sm,
          }}>
            {h.statement}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
            <Chip tone="info" title="number of candidate interventions in scope">
              {h.scope.candidates_total} candidates
            </Chip>
            {h.scope.targets_in_scope.slice(0, expanded ? 99 : 4).map(t => (
              <Chip key={t} tone="info" title="mechanistic target in scope">
                ◎ {t}
              </Chip>
            ))}
            {!expanded && h.scope.targets_in_scope.length > 4 && (
              <button onClick={() => setExpanded(true)} style={{
                background: "transparent", border: "none", color: color.textDim,
                fontSize: 10, cursor: "pointer", fontFamily: "inherit",
              }}>
                +{h.scope.targets_in_scope.length - 4} more targets
              </button>
            )}
            {h.scope.safety_screens_active.map(s => (
              <Chip key={s} tone={s.includes("hard-blocked") ? "block" : "warn"}
                    title="active safety screen derived from your medication list and findings">
                ⚠ {s}
              </Chip>
            ))}
            {h.is_example_profile && (
              <Chip tone="warn" title="synthetic profile — drop documents in the Corpus tab to anchor to real findings">
                example profile
              </Chip>
            )}
            <button onClick={() => setExpanded(v => !v)} style={{
              background: "transparent", border: "none", color: color.accent,
              fontSize: 10, cursor: "pointer", fontFamily: "inherit",
              marginLeft: "auto",
            }}>
              {expanded ? "− less" : "+ falsifiers · anchors"}
            </button>
          </div>

          {expanded && (
            <div style={{
              marginTop: space.md, padding: space.md,
              background: color.bg0, borderRadius: radius.sm,
              border: `1px solid ${color.border}`,
              display: "grid", gridTemplateColumns: "1fr 1fr", gap: space.lg,
              fontSize: 11,
            }}>
              <div>
                <div style={{ color: color.accent, fontSize: 10, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Patient anchors (used in retrieval queries)
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {h.scope.patient_anchors.map(a => (
                    <span key={a} style={{
                      padding: "2px 6px", background: color.bg2,
                      borderRadius: 3, color: color.textDim, fontSize: 10,
                    }}>{a}</span>
                  ))}
                </div>
              </div>
              <div>
                <div style={{ color: color.accent, fontSize: 10, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Falsifiers (what would knock a candidate off)
                </div>
                <ul style={{ margin: 0, paddingLeft: space.lg, color: color.textDim }}>
                  {h.falsifiers.map((f, i) => <li key={i} style={{ marginBottom: 3 }}>{f}</li>)}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};

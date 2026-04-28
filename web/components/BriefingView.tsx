import React, { useEffect, useState } from "react";
import { color, space, radius, SEVERITY_COLOR } from "../styles/tokens";
import { api, type Intervention } from "../lib/api";
import { Markdown } from "../lib/markdown";

export const BriefingView: React.FC<{
  intervention: Intervention;
  onRefresh: () => void;
}> = ({ intervention, onRefresh }) => {
  const [md, setMd] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.briefing(intervention.key)
      .then(d => setMd(d.markdown))
      .finally(() => setLoading(false));
  }, [intervention.key]);

  const refresh = async () => {
    setRefreshing(true);
    try {
      await api.refresh(intervention.key);
      // Poll briefly for new evidence to land.
      setTimeout(async () => {
        const d = await api.briefing(intervention.key);
        setMd(d.markdown);
        onRefresh();
        setRefreshing(false);
      }, 8000);
    } catch {
      setRefreshing(false);
    }
  };

  const sev = SEVERITY_COLOR[intervention.safety_overall] || color.textDim;

  return (
    <div style={{
      background: color.bg1, border: `1px solid ${color.border}`,
      borderRadius: radius.md, height: "100%",
      display: "grid", gridTemplateRows: "auto auto 1fr", overflow: "hidden",
    }}>
      <div style={{
        padding: space.md, borderBottom: `1px solid ${color.border}`,
        display: "flex", alignItems: "center", gap: space.md, flexWrap: "wrap",
      }}>
        <div style={{
          width: 12, height: 12, borderRadius: "50%", background: sev,
          boxShadow: `0 0 0 3px ${color.bg1}, 0 0 0 4px ${sev}40`,
        }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ color: color.text, fontSize: 14, fontWeight: 500 }}>
            {intervention.name}
          </div>
          <div style={{ color: color.textFaint, fontSize: 11, marginTop: 2 }}>
            {intervention.category} · expected tier {intervention.expected_tier}
            {" · "}seizure: {intervention.seizure_risk}
            {" · "}n={intervention.n_evidence}
          </div>
        </div>
        <button onClick={refresh} disabled={refreshing} style={{
          background: refreshing ? color.bg2 : color.bg3,
          color: refreshing ? color.textFaint : color.accent,
          border: `1px solid ${refreshing ? color.border : color.borderStrong}`,
          padding: `${space.xs}px ${space.md}px`, borderRadius: radius.sm,
          cursor: refreshing ? "wait" : "pointer", fontSize: 11,
          fontFamily: "inherit", whiteSpace: "nowrap",
        }}>
          {refreshing ? "fetching…" : "↻ refresh evidence"}
        </button>
      </div>

      {intervention.safety_flags.length > 0 && (
        <div style={{
          padding: `${space.sm}px ${space.md}px`,
          background: `${sev}15`, borderBottom: `1px solid ${color.border}`,
        }}>
          {intervention.safety_flags.map((f, i) => (
            <div key={i} style={{ fontSize: 11, color: color.text, marginBottom: 2 }}>
              <strong style={{ color: SEVERITY_COLOR[f.severity] }}>
                {f.severity.replace("_", " ").toUpperCase()}
              </strong>
              {" "}<span style={{ color: color.textDim }}>({f.axis})</span>{" "}
              {f.rationale}
            </div>
          ))}
        </div>
      )}

      <div style={{
        padding: space.lg, overflow: "auto", color: color.text,
      }}>
        {loading
          ? <div style={{ color: color.textFaint }}>loading briefing…</div>
          : <Markdown src={md} />}
      </div>
    </div>
  );
};

import React, { useEffect, useState } from "react";
import { color, space, radius, SEVERITY_COLOR } from "../styles/tokens";
import { PanelHeader } from "./PanelHeader";
import { api, type SchedulerState, type ActivityEvent, type Synopsis } from "../lib/api";

type Tab = "synopsis" | "loops" | "activity";

const fmtTime = (iso: string | null): string => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
};

const fmtRel = (iso: string | null): string => {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 0) {
    const s = Math.round(-ms / 1000);
    if (s < 60) return `in ${s}s`;
    if (s < 3600) return `in ${Math.round(s / 60)}m`;
    return `in ${Math.round(s / 3600)}h`;
  }
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  return `${Math.round(s / 3600)}h ago`;
};

export const TelemetryPanel: React.FC<{
  onSelectIntervention?: (key: string) => void;
}> = ({ onSelectIntervention }) => {
  const [tab, setTab] = useState<Tab>("synopsis");
  const [synopsis, setSynopsis] = useState<Synopsis | null>(null);
  const [state, setState] = useState<SchedulerState | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);

  const load = () => {
    api.synopsis().then(setSynopsis).catch(() => {});
    api.schedulerState().then(setState).catch(() => {});
    api.schedulerActivity(80).then(d => setActivity(d.events)).catch(() => {});
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <aside style={{
      background: color.bg1, borderLeft: `1px solid ${color.border}`,
      display: "grid", gridTemplateRows: "auto auto 1fr", overflow: "hidden",
      width: 380,
    }}>
      <PanelHeader
        title="Investigation cockpit"
        subtitle="rolled-up findings · live loop status · activity"
      />
      <nav style={{ display: "flex", borderBottom: `1px solid ${color.border}` }}>
        {(["synopsis", "loops", "activity"] as Tab[]).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            flex: 1, padding: `${space.sm}px ${space.md}px`,
            background: tab === t ? color.bg2 : "transparent",
            color: tab === t ? color.accent : color.textDim,
            border: "none",
            borderBottom: `2px solid ${tab === t ? color.accent : "transparent"}`,
            cursor: "pointer", fontSize: 11, textTransform: "uppercase",
            letterSpacing: "0.08em", fontFamily: "inherit",
          }}>{t}</button>
        ))}
      </nav>
      <div style={{ overflowY: "auto" }}>
        {tab === "synopsis" && <SynopsisTab data={synopsis} onSelect={onSelectIntervention} />}
        {tab === "loops" && <LoopsTab state={state} />}
        {tab === "activity" && <ActivityTab events={activity} onSelect={onSelectIntervention} />}
      </div>
    </aside>
  );
};

const Section: React.FC<{ title: string; children: React.ReactNode; hint?: string }> = ({ title, children, hint }) => (
  <div style={{ padding: `${space.md}px ${space.md}px ${space.sm}px`, borderBottom: `1px solid ${color.border}` }}>
    <div style={{
      color: color.textDim, fontSize: 10, textTransform: "uppercase",
      letterSpacing: "0.08em", marginBottom: 6,
      display: "flex", justifyContent: "space-between", alignItems: "baseline",
    }}>
      <span>{title}</span>
      {hint && <span style={{ color: color.textFaint, textTransform: "none", fontSize: 9 }}>{hint}</span>}
    </div>
    {children}
  </div>
);

const SynopsisTab: React.FC<{ data: Synopsis | null; onSelect?: (k: string) => void }> = ({ data, onSelect }) => {
  if (!data) return <div style={{ padding: space.md, color: color.textFaint }}>loading…</div>;
  const cov = data.coverage;
  return (
    <>
      <Section title="Coverage">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: space.sm, fontSize: 11 }}>
          <Stat label="seeded" value={`${cov.interventions_seeded}/${cov.interventions_total}`} />
          <Stat label="evidence" value={cov.evidence_rows.toLocaleString()} />
          <Stat label="updated" value={fmtRel(data.generated_at)} />
        </div>
      </Section>

      <Section title="Top of stack" hint="quality × plausibility">
        {data.top_interventions.length === 0
          ? <Empty>no seeded interventions yet</Empty>
          : data.top_interventions.map(t => (
            <button key={t.intervention_key} onClick={() => onSelect?.(t.intervention_key)}
                    style={{
                      width: "100%", textAlign: "left", background: "transparent",
                      border: "none", padding: "6px 0", cursor: "pointer",
                      borderBottom: `1px solid ${color.border}`, color: color.text,
                      fontFamily: "inherit",
                    }}>
              <div style={{
                display: "grid", gridTemplateColumns: "1fr auto", gap: space.sm,
                alignItems: "center", fontSize: 11,
              }}>
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {t.name} <span style={{ color: color.textFaint }}>· {t.category}</span>
                </span>
                <span style={{ color: color.accent, fontWeight: 600 }}>
                  {t.score.toFixed(2)}
                </span>
              </div>
            </button>
          ))}
      </Section>

      {data.target_clusters.length > 0 && (
        <Section title="Target clusters" hint="multiple candidates engaging the same mechanism">
          {data.target_clusters.map(c => (
            <div key={c.target_key} style={{ marginBottom: space.sm }}>
              <div style={{ color: color.t1, fontSize: 11, fontWeight: 500 }}>
                ◎ {c.target}{" "}
                <span style={{ color: color.textFaint, fontSize: 10 }}>
                  rel={c.patient_relevance.toFixed(2)} · {c.members.length} candidates
                </span>
              </div>
              <div style={{ paddingLeft: space.md, fontSize: 10, color: color.textDim }}>
                {c.members.map((m, i) => (
                  <span key={m.intervention_key}>
                    <button onClick={() => onSelect?.(m.intervention_key)} style={{
                      background: "transparent", border: "none", color: color.textDim,
                      cursor: "pointer", fontSize: 10, fontFamily: "inherit", padding: 0,
                    }}>{m.name}</button>
                    {i < c.members.length - 1 && " · "}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </Section>
      )}

      <Section title="Latest evidence" hint={`last 24h · ${data.recent_evidence.length} items`}>
        {data.recent_evidence.length === 0
          ? <Empty>no recent fetches</Empty>
          : data.recent_evidence.slice(0, 8).map((e, i) => (
            <div key={i} style={{
              padding: "6px 0", borderBottom: `1px solid ${color.border}`,
              fontSize: 11,
            }}>
              <a href={e.url} target="_blank" rel="noreferrer"
                 style={{ color: color.text, textDecoration: "none" }}>
                {e.title.slice(0, 96)}{e.title.length > 96 && "…"}
              </a>
              <div style={{ color: color.textFaint, fontSize: 10, marginTop: 2 }}>
                {e.source} · {e.tier} · {e.study_type}
                {e.evidence_quality != null && ` · q=${e.evidence_quality.toFixed(2)}`}
                {e.mechanistic_plausibility != null && ` · p=${e.mechanistic_plausibility.toFixed(2)}`}
              </div>
            </div>
          ))}
      </Section>
    </>
  );
};

const Stat: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div style={{
    background: color.bg2, border: `1px solid ${color.border}`,
    borderRadius: radius.sm, padding: 6,
  }}>
    <div style={{ color: color.textFaint, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
    <div style={{ color: color.text, fontSize: 12, marginTop: 2, fontWeight: 500 }}>{value}</div>
  </div>
);

const Empty: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ color: color.textFaint, fontSize: 11, fontStyle: "italic", padding: 4 }}>{children}</div>
);

const STATUS_COLOR: Record<string, string> = {
  idle: color.textFaint, sleeping: color.textDim,
  running: color.t2, error: color.block,
};

const LoopsTab: React.FC<{ state: SchedulerState | null }> = ({ state }) => {
  if (!state) return <div style={{ padding: space.md, color: color.textFaint }}>loading…</div>;
  return (
    <>
      <Section title="Process" hint={`up since ${fmtTime(state.started_at)}`}>
        <div style={{ fontSize: 11, color: color.textDim }}>
          {state.loops.length === 0
            ? <Empty>scheduler not yet observed (start API with NEUROFORGE_SCHEDULER=1)</Empty>
            : `${state.loops.length} loops registered, ${state.activity_count} events buffered`}
        </div>
      </Section>

      {state.loops.map(l => (
        <Section key={l.name} title={l.name} hint={`${l.total_ticks} tick${l.total_ticks === 1 ? "" : "s"}`}>
          <div style={{ fontSize: 11, lineHeight: 1.7 }}>
            <Row k="status" v={
              <span style={{ color: STATUS_COLOR[l.status] || color.text }}>● {l.status}</span>
            } />
            <Row k="last tick" v={fmtRel(l.last_tick)} />
            <Row k="next tick" v={fmtRel(l.next_tick)} />
            {l.last_intervention && <Row k="last intervention" v={l.last_intervention} />}
            {l.last_connector && <Row k="last connector" v={l.last_connector} />}
            <Row k="last result" v={`${l.last_result_count} rows`} />
            <Row k="evidence persisted" v={l.total_evidence_persisted} />
            {l.last_error && (
              <Row k="last error" v={<span style={{ color: color.block }}>{l.last_error.slice(0, 60)}</span>} />
            )}
          </div>
        </Section>
      ))}

      {state.queue.length > 0 && (
        <Section title="Upcoming queue" hint={`${state.queue.length} to go`}>
          <div style={{ fontSize: 11, color: color.textDim, lineHeight: 1.6 }}>
            {state.queue.slice(0, 12).join(" · ")}
            {state.queue.length > 12 && ` … +${state.queue.length - 12}`}
          </div>
        </Section>
      )}
    </>
  );
};

const Row: React.FC<{ k: string; v: React.ReactNode }> = ({ k, v }) => (
  <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: space.sm, color: color.text }}>
    <span style={{ color: color.textFaint }}>{k}</span>
    <span>{v}</span>
  </div>
);

const KIND_COLOR: Record<string, string> = {
  tick_start: color.t2,
  tick_end: color.ok,
  connector: color.text,
  persisted: color.ok,
  error: color.block,
  scheduled: color.accent,
};

const ActivityTab: React.FC<{ events: ActivityEvent[]; onSelect?: (k: string) => void }> = ({ events, onSelect }) => {
  if (events.length === 0) {
    return <div style={{ padding: space.md, color: color.textFaint, fontSize: 11 }}>
      no activity yet — scheduler tick activity will appear here in real time
    </div>;
  }
  return (
    <div style={{ padding: `${space.sm}px ${space.md}px` }}>
      {events.map((e, i) => (
        <div key={i} style={{
          padding: "5px 0", borderBottom: `1px solid ${color.border}`, fontSize: 11,
          display: "grid", gridTemplateColumns: "60px 14px 1fr", gap: space.sm,
          alignItems: "baseline",
        }}>
          <span style={{ color: color.textFaint, fontSize: 10 }}>{fmtTime(e.ts)}</span>
          <span style={{ color: KIND_COLOR[e.kind] || color.text, fontSize: 14, lineHeight: 1 }}>•</span>
          <div style={{ minWidth: 0 }}>
            <div style={{ color: KIND_COLOR[e.kind] || color.text, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              {e.kind}
              {e.connector && <span style={{ color: color.textDim }}> · {e.connector}</span>}
              {e.count != null && <span style={{ color: color.textDim }}> · {e.count} rows</span>}
            </div>
            <div style={{ color: color.text, marginTop: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {e.intervention && (
                <button onClick={() => onSelect?.(e.intervention!)} style={{
                  background: "transparent", border: "none", color: color.accent,
                  cursor: "pointer", fontFamily: "inherit", padding: 0, fontSize: 11,
                  marginRight: space.xs,
                }}>{e.intervention}</button>
              )}
              <span style={{ color: color.textDim }}>{e.message}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

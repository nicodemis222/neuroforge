import React, { useEffect, useState } from "react";
import { color, space, radius } from "../styles/tokens";
import { PanelHeader } from "./PanelHeader";
import { api, type PatientProfile } from "../lib/api";

const Section: React.FC<{ title: string; count?: number; children: React.ReactNode }> = ({ title, count, children }) => (
  <section style={{
    background: color.bg1, border: `1px solid ${color.border}`,
    borderRadius: radius.md, marginBottom: space.lg,
  }}>
    <header style={{
      padding: space.md, borderBottom: `1px solid ${color.border}`,
      display: "flex", justifyContent: "space-between", alignItems: "center",
    }}>
      <span style={{ color: color.accent, fontSize: 12, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.08em" }}>
        {title}
      </span>
      {count !== undefined && (
        <span style={{ color: color.textFaint, fontSize: 10 }}>{count}</span>
      )}
    </header>
    <div style={{ padding: space.md }}>{children}</div>
  </section>
);

const Empty: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ color: color.textFaint, fontSize: 12, fontStyle: "italic" }}>{children}</div>
);

export const ProfilePanel: React.FC = () => {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  useEffect(() => { api.profile().then(setProfile); }, []);

  if (!profile) return <div style={{ padding: space.xl, color: color.textFaint }}>loading…</div>;

  const isExample = profile.findings.every(f => f.label.startsWith("(example)"));

  return (
    <div style={{ display: "grid", gridTemplateRows: "auto 1fr", height: "100%", overflow: "hidden" }}>
      <PanelHeader
        title="Patient profile"
        subtitle="the lens through which retrieval is filtered, scored, and safety-screened"
      />
      <div style={{ padding: space.xl, overflow: "auto" }}>
      <div style={{ maxWidth: 880, margin: "0 auto" }}>
        <p style={{ color: color.textDim, fontSize: 12, marginTop: 0, marginBottom: space.lg }}>
          Loaded from <code>data/patient_corpus/profile.json</code> if present,
          otherwise the synthetic example. This is the data that drives the
          hypothesis statement, the safety screen axes, and the mechanistic
          plausibility scoring.
        </p>

        {isExample && (
          <div style={{
            background: "rgba(245,201,90,0.08)", border: `1px solid ${color.caution}`,
            color: color.caution, padding: space.md, borderRadius: radius.sm,
            fontSize: 12, marginBottom: space.lg,
          }}>
            ⚠ This is the synthetic example profile. Drop documents into the
            Corpus tab and run extract to anchor briefings to your real findings.
          </div>
        )}

        <div style={{
          display: "grid", gridTemplateColumns: "repeat(3, 1fr)",
          gap: space.md, marginBottom: space.lg,
        }}>
          <Stat label="Patient ref" value={profile.patient_ref} />
          <Stat label="Age" value={profile.age || "—"} />
          <Stat label="Sex" value={profile.sex} />
        </div>

        <Section title="Findings" count={profile.findings.length}>
          {profile.findings.length === 0 ? <Empty>no findings</Empty> :
            profile.findings.map((f, i) => (
              <div key={i} style={{
                padding: space.md, borderRadius: radius.sm,
                background: color.bg2, marginBottom: space.sm, fontSize: 12,
              }}>
                <div style={{ color: color.text, fontWeight: 500 }}>{f.label}</div>
                <div style={{ color: color.textDim, fontSize: 11, marginTop: 4 }}>
                  <strong>location:</strong> {f.location || "—"}
                  {" · "}<strong>chronicity:</strong> {f.chronicity || "—"}
                </div>
                {f.radiology_favored && (
                  <div style={{ color: color.textDim, fontSize: 11, marginTop: 2 }}>
                    <strong>favored:</strong> {f.radiology_favored}
                  </div>
                )}
                {f.differential.length > 0 && (
                  <div style={{ color: color.textDim, fontSize: 11, marginTop: 2 }}>
                    <strong>ddx:</strong> {f.differential.join(" · ")}
                  </div>
                )}
                {f.source_doc && (
                  <div style={{ color: color.textFaint, fontSize: 10, marginTop: 4 }}>
                    source: {f.source_doc}
                  </div>
                )}
              </div>
            ))}
        </Section>

        <Section title="Symptoms" count={profile.symptoms.length}>
          {profile.symptoms.length === 0 ? <Empty>no symptoms</Empty> :
            profile.symptoms.map((s, i) => (
              <div key={i} style={{
                padding: space.md, borderRadius: radius.sm,
                background: color.bg2, marginBottom: space.sm, fontSize: 12,
              }}>
                <div style={{ color: color.text, fontWeight: 500 }}>{s.label}</div>
                <div style={{ color: color.textDim, fontSize: 11, marginTop: 4 }}>
                  {[s.laterality, s.onset, s.duration, s.frequency].filter(Boolean).join(" · ")}
                </div>
                {s.triggers.length > 0 && (
                  <div style={{ color: color.textDim, fontSize: 11, marginTop: 2 }}>
                    triggers: {s.triggers.join(", ")}
                  </div>
                )}
              </div>
            ))}
        </Section>

        <Section title="Medications" count={profile.medications.length}>
          {profile.medications.length === 0 ? <Empty>no medications listed</Empty> :
            <div style={{ display: "flex", flexWrap: "wrap", gap: space.sm }}>
              {profile.medications.map((m, i) => (
                <span key={i} style={{
                  padding: `${space.xs}px ${space.md}px`, borderRadius: 999,
                  background: color.bg3, color: color.text, fontSize: 11,
                  border: `1px solid ${color.border}`,
                }}>{m}</span>
              ))}
            </div>}
        </Section>

        <Section title="Diagnoses (open)" count={profile.diagnoses_open.length}>
          {profile.diagnoses_open.length === 0 ? <Empty>none</Empty> :
            <ul style={{ margin: 0, paddingLeft: space.lg, color: color.text, fontSize: 12 }}>
              {profile.diagnoses_open.map((d, i) => <li key={i} style={{ marginBottom: 4 }}>{d}</li>)}
            </ul>}
        </Section>

        <Section title="Diagnoses (ruled out)" count={profile.diagnoses_ruled_out.length}>
          {profile.diagnoses_ruled_out.length === 0 ? <Empty>none</Empty> :
            <ul style={{ margin: 0, paddingLeft: space.lg, color: color.textDim, fontSize: 12 }}>
              {profile.diagnoses_ruled_out.map((d, i) => <li key={i} style={{ marginBottom: 4 }}>{d}</li>)}
            </ul>}
        </Section>

        <Section title="Risk factors" count={profile.risk_factors.length}>
          {profile.risk_factors.length === 0 ? <Empty>none</Empty> :
            <ul style={{ margin: 0, paddingLeft: space.lg, color: color.text, fontSize: 12 }}>
              {profile.risk_factors.map((d, i) => <li key={i} style={{ marginBottom: 4 }}>{d}</li>)}
            </ul>}
        </Section>
      </div>
      </div>
    </div>
  );
};

const Stat: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div style={{
    background: color.bg1, border: `1px solid ${color.border}`,
    borderRadius: radius.sm, padding: space.md,
  }}>
    <div style={{ color: color.textFaint, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>
      {label}
    </div>
    <div style={{ color: color.text, fontSize: 14, marginTop: 2 }}>{value}</div>
  </div>
);

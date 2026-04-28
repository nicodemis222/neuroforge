import { useCallback, useEffect, useState } from "react";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { Scatter } from "../components/Scatter";
import { BriefingView } from "../components/BriefingView";
import { CorpusPanel } from "../components/CorpusPanel";
import { ProfilePanel } from "../components/ProfilePanel";
import { color, space } from "../styles/tokens";
import { api, type Intervention, type PatientProfile } from "../lib/api";

type Tab = "dashboard" | "corpus" | "profile";

export default function Home() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [items, setItems] = useState<Intervention[]>([]);
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [schedulerOn, setSchedulerOn] = useState(false);

  const refreshItems = useCallback(() =>
    api.interventions().then(setItems), []);
  const refreshProfile = useCallback(() =>
    api.profile().then(setProfile), []);

  useEffect(() => {
    refreshItems();
    refreshProfile();
    api.initStatus().then(s => setSchedulerOn(!!s.scheduler_on));
    const t = setInterval(() => {
      refreshItems();
      api.initStatus().then(s => setSchedulerOn(!!s.scheduler_on)).catch(() => {});
    }, 30000);
    return () => clearInterval(t);
  }, [refreshItems, refreshProfile]);

  const totalEvidence = items.reduce((s, i) => s + i.n_evidence, 0);
  const selectedItem = items.find(i => i.key === selected) || null;

  return (
    <div style={{
      height: "100vh", display: "grid",
      gridTemplateRows: "auto 1fr", background: color.bg0,
    }}>
      <Header
        tab={tab} setTab={setTab}
        profile={profile}
        totalEvidence={totalEvidence}
        schedulerOn={schedulerOn}
      />

      {tab === "dashboard" && (
        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", overflow: "hidden" }}>
          <Sidebar items={items} selected={selected} onSelect={setSelected} />
          <main style={{
            padding: space.md, display: "grid",
            gridTemplateColumns: selectedItem ? "1fr 1fr" : "1fr",
            gap: space.md, overflow: "hidden",
          }}>
            <div style={{ minHeight: 0 }}>
              <Scatter items={items} selected={selected} onSelect={setSelected} />
            </div>
            {selectedItem && (
              <div style={{ minHeight: 0, overflow: "hidden" }}>
                <BriefingView intervention={selectedItem} onRefresh={refreshItems} />
              </div>
            )}
          </main>
        </div>
      )}

      {tab === "corpus" && <CorpusPanel />}
      {tab === "profile" && <ProfilePanel />}
    </div>
  );
}

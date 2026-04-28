import { useCallback, useEffect, useState } from "react";
import { Header } from "../components/Header";
import { HypothesisBar } from "../components/HypothesisBar";
import { Sidebar } from "../components/Sidebar";
import { Scatter } from "../components/Scatter";
import { BriefingView } from "../components/BriefingView";
import { CorpusPanel } from "../components/CorpusPanel";
import { ProfilePanel } from "../components/ProfilePanel";
import { TelemetryPanel } from "../components/TelemetryPanel";
import { color, space } from "../styles/tokens";
import { useFilters } from "../lib/filters";
import { api, type Intervention, type PatientProfile } from "../lib/api";

type Tab = "dashboard" | "corpus" | "profile";

export default function Home() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [items, setItems] = useState<Intervention[]>([]);
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [schedulerOn, setSchedulerOn] = useState(false);

  const { filters, filtered, toggle, reset, setQ, setHideEmpty, isActive } = useFilters(items);

  const refreshItems = useCallback(() => api.interventions().then(setItems), []);
  const refreshProfile = useCallback(() => api.profile().then(setProfile), []);

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
      gridTemplateRows: "auto auto 1fr", background: color.bg0,
    }}>
      <Header
        tab={tab} setTab={setTab}
        profile={profile}
        totalEvidence={totalEvidence}
        schedulerOn={schedulerOn}
      />

      {tab === "dashboard" && <HypothesisBar />}

      {tab === "dashboard" && (
        <div style={{
          display: "grid", gridTemplateColumns: "auto 1fr auto",
          overflow: "hidden",
        }}>
          <Sidebar items={items} filtered={filtered} filters={filters}
                   toggleFilter={toggle} setQ={setQ} setHideEmpty={setHideEmpty}
                   resetFilters={reset} isFilterActive={isActive}
                   selected={selected} onSelect={setSelected} />
          <main style={{
            padding: space.md, display: "grid",
            gridTemplateRows: selectedItem ? "1fr 1fr" : "1fr",
            gap: space.md, overflow: "hidden",
          }}>
            <div style={{ minHeight: 0 }}>
              <Scatter items={filtered} totalItems={items.length}
                       selected={selected} onSelect={setSelected} />
            </div>
            {selectedItem && (
              <div style={{ minHeight: 0, overflow: "hidden" }}>
                <BriefingView intervention={selectedItem} onRefresh={refreshItems} />
              </div>
            )}
          </main>
          <TelemetryPanel onSelectIntervention={setSelected} />
        </div>
      )}

      {tab === "corpus" && <CorpusPanel />}
      {tab === "profile" && <ProfilePanel />}
    </div>
  );
}

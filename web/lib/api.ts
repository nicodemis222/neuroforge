/** Thin typed API client. */

export type SafetyFlag = { severity: string; axis: string; rationale: string };

export type Intervention = {
  key: string;
  name: string;
  category: string;
  targets: string[];
  expected_tier: string;
  seizure_risk: string;
  interactions: string[];
  notes: string;
  n_evidence: number;
  mean_quality: number | null;
  mean_plausibility: number | null;
  safety_overall: string;
  safety_flags: SafetyFlag[];
};

export type Finding = {
  label: string; location: string; chronicity: string;
  radiology_favored: string; differential: string[]; source_doc: string;
};
export type Symptom = {
  label: string; laterality: string; onset: string;
  duration: string; frequency: string; triggers: string[];
};
export type PatientProfile = {
  patient_ref: string; age: number; sex: string;
  findings: Finding[]; symptoms: Symptom[];
  medications: string[]; diagnoses_open: string[];
  diagnoses_ruled_out: string[]; risk_factors: string[];
};

export type CorpusFile = {
  name: string; size_bytes: number; supported: boolean; ext: string;
};
export type CorpusListing = {
  files: CorpusFile[]; supported_extensions: string[];
};

const j = <T>(r: Response) => r.json() as Promise<T>;

export type Hypothesis = {
  statement: string;
  is_example_profile: boolean;
  scope: {
    targets_in_scope: string[];
    patient_anchors: string[];
    candidates_total: number;
    safety_screens_active: string[];
  };
  falsifiers: string[];
  context: {
    has_seizure_concern: boolean;
    on_asm: boolean;
    on_serotonergic: string[];
    on_catecholaminergic: string[];
  };
};

export type Synopsis = {
  generated_at: string;
  coverage: {
    interventions_total: number;
    interventions_seeded: number;
    evidence_rows: number;
  };
  safety_distribution: Record<string, number>;
  top_interventions: {
    intervention_key: string; name: string; category: string;
    n_evidence: number; mean_quality: number; mean_plausibility: number;
    score: number;
  }[];
  recent_evidence: {
    title: string; url: string; tier: string; source: string;
    study_type: string; fetched_at: string;
    intervention_keys: string;
    evidence_quality: number | null;
    mechanistic_plausibility: number | null;
  }[];
  target_clusters: {
    target_key: string; target: string; patient_relevance: number;
    members: { intervention_key: string; name: string; score: number }[];
  }[];
};

export type LoopState = {
  name: string; status: string;
  last_tick: string | null; next_tick: string | null;
  last_intervention: string | null; last_connector: string | null;
  last_result_count: number; last_error: string | null;
  total_ticks: number; total_evidence_persisted: number;
};

export type SchedulerState = {
  started_at: string; now: string;
  loops: LoopState[]; queue: string[]; activity_count: number;
};

export type ActivityEvent = {
  ts: string; kind: string;
  loop: string | null; intervention: string | null; connector: string | null;
  message: string; count: number | null;
};

export type Rationale = {
  intervention_key: string; name: string;
  category: string; expected_tier: string; seizure_risk: string;
  interactions: string[]; notes: string;
  targets: { key: string; canonical: string; mechanism: string;
             patient_relevance: number; notes: string }[];
  patient_anatomy_hits: string[];
  rationale: string;
};

export const api = {
  initStatus: () => fetch("/api/init/status").then(j<any>),
  profile: () => fetch("/api/profile").then(j<PatientProfile>),
  interventions: () =>
    fetch("/api/ontology/interventions").then(j<Intervention[]>),
  briefing: (key: string) =>
    fetch(`/api/intervention/${key}/briefing`).then(j<{ markdown: string }>),
  refresh: (key: string) =>
    fetch(`/api/intervention/${key}/refresh`, { method: "POST" }).then(j<any>),

  hypothesis: () => fetch("/api/hypothesis").then(j<Hypothesis>),
  synopsis: () => fetch("/api/synopsis").then(j<Synopsis>),
  schedulerState: () => fetch("/api/scheduler/state").then(j<SchedulerState>),
  schedulerActivity: (limit = 100) =>
    fetch(`/api/scheduler/activity?limit=${limit}`).then(j<{ events: ActivityEvent[] }>),
  rationale: (key: string) =>
    fetch(`/api/intervention/${key}/rationale`).then(j<Rationale>),

  corpusList: () => fetch("/api/corpus").then(j<CorpusListing>),
  corpusUpload: (files: File[]) => {
    const fd = new FormData();
    files.forEach(f => fd.append("files", f));
    return fetch("/api/corpus/upload", { method: "POST", body: fd }).then(j<any>);
  },
  corpusDelete: (name: string) =>
    fetch(`/api/corpus/${encodeURIComponent(name)}`, { method: "DELETE" }).then(j<any>),
  corpusExtract: () =>
    fetch("/api/corpus/extract", { method: "POST" }).then(j<any>),
};

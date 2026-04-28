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

export const api = {
  initStatus: () => fetch("/api/init/status").then(j<any>),
  profile: () => fetch("/api/profile").then(j<PatientProfile>),
  interventions: () =>
    fetch("/api/ontology/interventions").then(j<Intervention[]>),
  briefing: (key: string) =>
    fetch(`/api/intervention/${key}/briefing`).then(j<{ markdown: string }>),
  refresh: (key: string) =>
    fetch(`/api/intervention/${key}/refresh`, { method: "POST" }).then(j<any>),

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

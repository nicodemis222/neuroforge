"""
Patient profile — the *lens* through which retrieval is filtered and scored.

The shipped DEFAULT is a fully synthetic example so the platform boots
with something to demonstrate the schema. Real patient data comes from
documents the user drops into `data/patient_corpus/` and an extraction
pass that writes `profile.json` (which this loader prefers over DEFAULT).

Anything in this file is committed to the repo; anything in
`data/patient_corpus/` is gitignored.
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
import json


@dataclass
class Finding:
    label: str
    location: str             # neuroanatomy
    chronicity: str           # acute | subacute | chronic | unknown
    radiology_favored: str    # most-likely interpretation per radiologist
    differential: list[str]
    source_doc: str


@dataclass
class Symptom:
    label: str
    laterality: str
    onset: str
    duration: str
    frequency: str
    triggers: list[str]


@dataclass
class PatientProfile:
    patient_ref: str
    age: int
    sex: str
    findings: list[Finding] = field(default_factory=list)
    symptoms: list[Symptom] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    diagnoses_open: list[str] = field(default_factory=list)
    diagnoses_ruled_out: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


# ----------------------------------------------------------------------
# DEFAULT — synthetic example. Replace at runtime by writing
# data/patient_corpus/profile.json (the extractor produces this from
# uploaded documents). DO NOT put real patient data here.
# ----------------------------------------------------------------------
DEFAULT = PatientProfile(
    patient_ref="example-patient",
    age=0,
    sex="unspecified",
    findings=[
        Finding(
            label="(example) Chronic white-matter signal abnormality, corticospinal tract",
            location="(example) corticospinal tract",
            chronicity="chronic",
            radiology_favored="(example) remote ischemic injury",
            differential=["(example) chronic demyelinating plaque"],
            source_doc="(synthetic example — replace by ingesting your own reports)",
        ),
    ],
    symptoms=[
        Symptom(
            label="(example) Recurrent stereotyped focal sensory episodes",
            laterality="(example) unilateral",
            onset="(example) childhood",
            duration="(example) minutes",
            frequency="(example) variable",
            triggers=["(example) stress"],
        ),
    ],
    medications=[],
    diagnoses_open=[
        "(example) Focal aware seizures vs. migraine variant",
    ],
    diagnoses_ruled_out=[],
    risk_factors=[],
)


def _profile_json_path() -> Path:
    # services/api/app/seed/patient_profile.py -> data/patient_corpus/profile.json
    return (Path(__file__).resolve().parents[4]
            / "data" / "patient_corpus" / "profile.json")


def load() -> PatientProfile:
    """Load patient profile, preferring extracted JSON if present."""
    p = _profile_json_path()
    if p.exists():
        data = json.loads(p.read_text())
        findings = [Finding(**f) for f in data.pop("findings", [])]
        symptoms = [Symptom(**s) for s in data.pop("symptoms", [])]
        return PatientProfile(findings=findings, symptoms=symptoms, **data)
    return DEFAULT


def patient_keywords(profile: PatientProfile) -> list[str]:
    """Search-side keywords derived from the profile.

    Generic neuro-recovery anchors are always included. Profile-specific
    anchors are appended when present so retrieval biases toward the
    actual lesion + symptom set.
    """
    base = [
        "neuronal regrowth",
        "axonal sprouting",
        "remyelination",
        "neurogenesis",
        "white matter injury recovery",
    ]
    anchors: list[str] = []
    for f in profile.findings:
        for term in (f.location, f.label, f.radiology_favored):
            if term and not term.startswith("(example)"):
                anchors.append(term)
    for s in profile.symptoms:
        if s.label and not s.label.startswith("(example)"):
            anchors.append(s.label)
    # Dedupe preserving order
    seen, out = set(), []
    for k in (*anchors, *base):
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


if __name__ == "__main__":
    print(load().to_json())

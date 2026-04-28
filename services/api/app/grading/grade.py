"""
Evidence grading. We compute two axes for every retrieved Evidence:

  - evidence_quality  (0..1, GRADE-inspired)
  - mechanistic_plausibility  (0..1, derived from target/intervention
    overlap with the patient profile)

The UI plots these as a 2D scatter; the briefing layer ranks within
quartiles. Tier is the strongest prior on quality but we adjust for
study_type, recency, and source-reputation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.connectors.base import Evidence
from app.ontology import INTERVENTIONS_BY_KEY, TARGETS_BY_KEY
from app.seed import PatientProfile

# --- Evidence-quality priors per tier ---
TIER_PRIOR = {"T1": 0.75, "T2": 0.65, "T3": 0.45, "T4": 0.25, "T5": 0.15}

# --- Study-type modifiers ---
STUDY_MOD = {
    "systematic_review": +0.20,
    "rct": +0.15,
    "cohort": +0.05,
    "review": +0.02,
    "preprint": -0.05,
    "case": -0.05,
    "preclinical": -0.10,
    "patent": -0.05,
    "community": -0.20,
    "unknown": 0.0,
}

# --- Source-reputation overrides ---
SOURCE_BONUS = {
    "pubmed": +0.05,
    "europe_pmc": +0.05,
    "clinicaltrials": +0.05,
    "openfda": +0.10,
    "fringe:examine": +0.05,        # examine.com cites primaries
    "rss:cochrane_neuro": +0.10,
    "rss:nature_neurosci": +0.05,
}


@dataclass
class Grade:
    evidence_quality: float
    mechanistic_plausibility: float
    rationale: str


def _recency(evidence: Evidence) -> float:
    if not evidence.published:
        return 0.0
    age_days = (datetime.now(timezone.utc) - evidence.published).days
    if age_days < 365:
        return +0.05
    if age_days < 365 * 5:
        return 0.0
    if age_days < 365 * 10:
        return -0.02
    return -0.05


def _quality(evidence: Evidence) -> float:
    base = TIER_PRIOR.get(evidence.tier, 0.3)
    base += STUDY_MOD.get(evidence.study_type, 0.0)
    base += SOURCE_BONUS.get(evidence.source, 0.0)
    base += _recency(evidence)
    return max(0.0, min(1.0, base))


def _plausibility(evidence: Evidence, profile: PatientProfile) -> float:
    """Mechanistic plausibility = how close the targeted mechanism is to the
    patient's lesion + symptom profile."""
    score = 0.0
    for tk in evidence.target_keys:
        t = TARGETS_BY_KEY.get(tk)
        if t:
            score = max(score, t.patient_relevance)
    # Bonus if title/abstract mentions patient-anatomy keywords.
    text = f"{evidence.title} {evidence.abstract}".lower()
    anatomy_hits = sum(1 for kw in (
        "corticospinal", "internal capsule", "cerebral peduncle",
        "crossed cerebellar", "diaschisis", "periventricular",
        "remyelination", "axonal sprouting", "oligodendrocyte progenitor",
        "focal aware seizure",
    ) if kw in text)
    score = min(1.0, score + 0.05 * anatomy_hits)
    # Intervention-side bonus if the paper actually studies an intervention
    # we track.
    for ik in evidence.intervention_keys:
        iv = INTERVENTIONS_BY_KEY.get(ik)
        if iv and iv.targets:
            score += 0.05
    return max(0.0, min(1.0, score))


def grade(evidence: Evidence, profile: PatientProfile) -> Grade:
    q = _quality(evidence)
    p = _plausibility(evidence, profile)
    rationale = (f"tier={evidence.tier}; study={evidence.study_type}; "
                 f"source={evidence.source}; q={q:.2f}; p={p:.2f}")
    return Grade(evidence_quality=q, mechanistic_plausibility=p, rationale=rationale)

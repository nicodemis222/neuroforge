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
    patient's lesion + symptom profile.

    Designed to *spread* — anatomy-keyword hits are required for top scores,
    so an evidence row with target match but no anatomy mention sits in the
    mid-range, not pinned to 1.0.
    """
    # Base from target relevance, but discounted so target alone caps at ~0.55.
    base = 0.0
    for tk in evidence.target_keys:
        t = TARGETS_BY_KEY.get(tk)
        if t:
            base = max(base, t.patient_relevance * 0.55)

    text = f"{evidence.title} {evidence.abstract}".lower()
    profile_anchors = []
    for f in profile.findings:
        for s in (f.label, f.location, f.radiology_favored):
            if s and not s.startswith("(example)"):
                profile_anchors.append(s.lower())
    for sym in profile.symptoms:
        if sym.label and not sym.label.startswith("(example)"):
            profile_anchors.append(sym.label.lower())

    # Generic neuro-recovery vocabulary (always counted).
    generic_kw = (
        "corticospinal", "internal capsule", "cerebral peduncle",
        "crossed cerebellar", "diaschisis", "periventricular",
        "remyelination", "axonal sprouting", "axon regeneration",
        "oligodendrocyte progenitor", "focal aware seizure",
        "white matter", "demyelination", "ischemic", "stroke recovery",
        "neuroplasticity", "neurogenesis",
    )
    generic_hits = sum(1 for kw in generic_kw if kw in text)

    # Profile-specific phrase hits (each 4-char-or-longer word).
    specific_hits = 0
    for anchor in profile_anchors:
        for word in anchor.split():
            if len(word) >= 5 and word in text:
                specific_hits += 1
                break

    # Intervention category match — a known intervention term in the abstract
    # gives a small confidence bump.
    iv_hits = 0
    for ik in evidence.intervention_keys:
        iv = INTERVENTIONS_BY_KEY.get(ik)
        if iv and iv.name.lower() in text:
            iv_hits += 1

    score = base + 0.07 * generic_hits + 0.05 * specific_hits + 0.04 * iv_hits
    # Slight randomization-resistant differentiator: study type modifier
    # nudges plausibility apart so RCTs don't sit on top of preclinicals.
    if evidence.study_type == "rct":
        score += 0.02
    elif evidence.study_type == "preclinical":
        score -= 0.03
    elif evidence.study_type == "community":
        score -= 0.05
    return max(0.0, min(1.0, score))


def grade(evidence: Evidence, profile: PatientProfile) -> Grade:
    q = _quality(evidence)
    p = _plausibility(evidence, profile)
    rationale = (f"tier={evidence.tier}; study={evidence.study_type}; "
                 f"source={evidence.source}; q={q:.2f}; p={p:.2f}")
    return Grade(evidence_quality=q, mechanistic_plausibility=p, rationale=rationale)

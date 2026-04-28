"""
/api/hypothesis    — falsifiable research framing derived from profile
/api/synopsis      — cross-intervention rolled-up findings
/api/scheduler/state    — live loop telemetry
/api/scheduler/activity — recent activity ring buffer
/api/intervention/{key}/rationale — why this intervention is a candidate
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.briefing import hypothesis as hyp
from app.briefing import synopsis
from app.ontology import INTERVENTIONS_BY_KEY, TARGETS_BY_KEY
from app.scheduler.telemetry import telemetry
from app.seed import load as load_profile

router = APIRouter(tags=["research"])


@router.get("/api/hypothesis")
def hypothesis() -> dict:
    return hyp.generate()


@router.get("/api/synopsis")
def syn() -> dict:
    return synopsis.generate()


@router.get("/api/scheduler/state")
def scheduler_state() -> dict:
    return telemetry.snapshot()


@router.get("/api/scheduler/activity")
def scheduler_activity(limit: int = 100) -> dict:
    return {"events": telemetry.recent_activity(limit=min(limit, 500))}


@router.get("/api/intervention/{key}/rationale")
def rationale(key: str) -> dict:
    iv = INTERVENTIONS_BY_KEY.get(key)
    if not iv:
        raise HTTPException(404)
    profile = load_profile()
    targets = []
    for tk in iv.targets:
        t = TARGETS_BY_KEY.get(tk)
        if t:
            targets.append({
                "key": t.key,
                "canonical": t.canonical,
                "mechanism": t.mechanism,
                "patient_relevance": t.patient_relevance,
                "notes": t.notes,
            })
    # Naive anatomy/keyword overlap
    profile_text = " ".join([
        *(f.label.lower() for f in profile.findings),
        *(f.location.lower() for f in profile.findings),
        *(s.label.lower() for s in profile.symptoms),
    ])
    anatomy_hits = []
    for kw in ("corticospinal", "internal capsule", "cerebral peduncle",
               "diaschisis", "periventricular", "cerebellar", "white matter",
               "demyelination", "ischemic", "seizure", "epilep", "migraine"):
        if kw in profile_text:
            anatomy_hits.append(kw)
    return {
        "intervention_key": key,
        "name": iv.name,
        "category": iv.category,
        "expected_tier": iv.expected_tier,
        "seizure_risk": iv.seizure_risk,
        "interactions": list(iv.interactions),
        "notes": iv.notes,
        "targets": targets,
        "patient_anatomy_hits": anatomy_hits,
        "rationale": _rationale_text(iv, targets, anatomy_hits),
    }


def _rationale_text(iv, targets: list[dict], anatomy_hits: list[str]) -> str:
    parts = []
    if iv.notes:
        parts.append(iv.notes)
    if targets:
        target_phrases = [
            f"{t['canonical']} ({t['mechanism']}, relevance {t['patient_relevance']:.2f})"
            for t in targets
        ]
        parts.append("Engages: " + "; ".join(target_phrases) + ".")
    if anatomy_hits:
        parts.append(
            "Patient anatomy/diagnosis keywords this intervention's evidence "
            "tends to overlap with: " + ", ".join(anatomy_hits) + "."
        )
    if iv.seizure_risk and iv.seizure_risk != "neutral":
        parts.append(f"Seizure-threshold profile: {iv.seizure_risk}.")
    if not parts:
        parts.append(
            f"Listed in the {iv.category} category at expected tier "
            f"{iv.expected_tier}. No dedicated mechanism notes; review "
            f"retrieved evidence for direct hypothesis fit."
        )
    return " ".join(parts)

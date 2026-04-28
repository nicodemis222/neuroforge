"""
The current research hypothesis derived from the loaded patient profile
and the active ontology.

A hypothesis here is the falsifiable claim the platform is collecting
evidence against:

  "Among interventions promoting <process_targets>, which are <safety-cleared>
   for this patient's profile <anatomy/findings/meds>, and rank highest in
   evidence × plausibility?"

The hypothesis pane in the UI exposes:
  - statement (the question)
  - scope (chips: targets in scope, anatomy anchors, screen-against meds,
           seizure-axis status, total candidates)
  - falsifiers (what evidence would knock a candidate off the list)
"""

from __future__ import annotations

from app.ontology import INTERVENTIONS_BY_KEY, TARGETS_BY_KEY
from app.safety import derive_context
from app.seed import load as load_profile, patient_keywords


def _process_targets() -> list[str]:
    """The high-relevance process/cellular targets we're optimizing for."""
    return [
        t.canonical for t in TARGETS_BY_KEY.values()
        if t.mechanism in ("process", "cell") and t.patient_relevance >= 0.85
    ]


def generate() -> dict:
    profile = load_profile()
    ctx = derive_context(profile)
    anchors = patient_keywords(profile)
    is_example = profile.patient_ref == "example-patient" or all(
        f.label.startswith("(example)") for f in profile.findings)

    targets = _process_targets()
    safety_screens = []
    if ctx.has_seizure_concern:
        if ctx.on_asm:
            safety_screens.append("seizure (covered by ASM)")
        else:
            safety_screens.append("seizure (no ASM — pro-convulsants hard-blocked)")
    if ctx.on_serotonergic:
        safety_screens.append(f"serotonergic ({', '.join(ctx.on_serotonergic)})")
    if ctx.on_catecholaminergic:
        safety_screens.append(f"catecholaminergic ({', '.join(ctx.on_catecholaminergic)})")

    candidates = list(INTERVENTIONS_BY_KEY.values())

    if is_example:
        statement = (
            "Demonstration mode — load real documents in the Corpus tab to "
            "anchor this hypothesis to your actual findings. Currently testing: "
            "which interventions in the catalog promote neuronal regrowth, "
            "remyelination, or NGF/BDNF expression in a generic profile?"
        )
    else:
        statement = (
            f"Among ~{len(candidates)} candidate interventions across drug, "
            f"biologic, supplement, behavioral, device, and holistic categories, "
            f"which best promote {', '.join(targets[:3])} (and adjacent "
            f"mechanisms) AND remain safety-cleared given this patient's "
            f"profile, ranked by evidence quality × mechanistic plausibility?"
        )

    falsifiers = [
        "High-quality RCT showing no benefit on a directly relevant outcome",
        "Mechanistic study disproving target engagement at clinically achievable dose",
        "New medication added to profile that triggers a hard-block (lifts the candidate off the considered list)",
        "Patient-anatomy mismatch (e.g. evidence is acute-injury only when patient lesion is chronic)",
    ]

    return {
        "statement": statement,
        "is_example_profile": is_example,
        "scope": {
            "targets_in_scope": targets,
            "patient_anchors": anchors[:8],
            "candidates_total": len(candidates),
            "safety_screens_active": safety_screens,
        },
        "falsifiers": falsifiers,
        "context": {
            "has_seizure_concern": ctx.has_seizure_concern,
            "on_asm": ctx.on_asm,
            "on_serotonergic": ctx.on_serotonergic,
            "on_catecholaminergic": ctx.on_catecholaminergic,
        },
    }

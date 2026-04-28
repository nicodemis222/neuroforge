"""
Safety screen — runs every candidate intervention against the loaded
patient profile. Three concerns dominate the neuroregeneration design space:

  1. Seizure threshold — if the profile lists suspected/active seizures
     and no antiseizure medication, anything that lowers threshold is
     hard-blocked.
  2. Serotonergic load — if the profile contains an SSRI/SNRI/serotonin
     modulator, strongly serotonergic interventions are hard-blocked
     (serotonin syndrome).
  3. Catecholaminergic load — if the profile contains an NRI/stimulant,
     strongly sympathomimetic interventions are downgraded.

Output is a structured `SafetyVerdict` consumed by the briefing layer
and the UI. Never auto-promote a HARD_BLOCK to a recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.ontology import Intervention, INTERVENTIONS_BY_KEY
from app.seed.patient_profile import PatientProfile, load as load_profile


class Severity(str, Enum):
    OK = "ok"
    CAUTION = "caution"
    WARN = "warn"
    HARD_BLOCK = "hard_block"


@dataclass
class SafetyFlag:
    severity: Severity
    axis: str            # 'seizure' | 'serotonergic' | 'catecholaminergic' | 'other'
    rationale: str


@dataclass
class SafetyVerdict:
    intervention_key: str
    overall: Severity
    flags: list[SafetyFlag] = field(default_factory=list)

    @property
    def is_blocking(self) -> bool:
        return self.overall == Severity.HARD_BLOCK


# Drug-class taxonomies (lowercase, substring-matched against profile.medications)
SEROTONERGIC_RX = {
    "ssri", "snri", "vortioxetine", "fluoxetine", "sertraline", "paroxetine",
    "citalopram", "escitalopram", "venlafaxine", "duloxetine", "mirtazapine",
    "trazodone", "moclobemide", "selegiline", "tramadol", "linezolid",
    "lithium",
}
CATECHOLAMINERGIC_RX = {
    "atomoxetine", "methylphenidate", "amphetamine", "lisdexamfetamine",
    "dextroamphetamine", "modafinil", "armodafinil", "bupropion",
    "phentermine",
}
ANTISEIZURE_RX = {
    "levetiracetam", "lamotrigine", "valproate", "valproic", "topiramate",
    "carbamazepine", "oxcarbazepine", "lacosamide", "phenytoin",
    "zonisamide", "clobazam", "clonazepam", "perampanel", "brivaracetam",
    "ethosuximide", "gabapentin", "pregabalin", "phenobarbital",
}

SEIZURE_KEYWORDS = (
    "seizure", "epilep", "ictal", "convulsion", "spell", "aura",
)


# Specific intervention keys that warrant hard contraindications regardless
# of dose, when stacked with serotonergic/catecholaminergic baseline meds.
STRONG_SEROTONERGIC = {"psilocybin", "dmt", "lithium_micro"}
STRONG_CATECHOLAMINERGIC = {"semax"}


@dataclass(frozen=True)
class PatientContext:
    has_seizure_concern: bool
    on_asm: bool
    on_serotonergic: list[str]
    on_catecholaminergic: list[str]


def _profile_meds_lower(profile: PatientProfile) -> list[str]:
    return [m.lower() for m in profile.medications if m]


def derive_context(profile: PatientProfile | None = None) -> PatientContext:
    profile = profile or load_profile()
    meds = _profile_meds_lower(profile)
    text_haystack = " ".join([
        *(f.label.lower() for f in profile.findings),
        *(s.label.lower() for s in profile.symptoms),
        *(d.lower() for d in profile.diagnoses_open),
        *(d.lower() for d in profile.diagnoses_ruled_out),
    ])
    has_seizure_concern = any(k in text_haystack for k in SEIZURE_KEYWORDS)
    on_asm = any(any(asm in m for asm in ANTISEIZURE_RX) for m in meds)
    on_serotonergic = [m for m in meds
                       if any(s in m for s in SEROTONERGIC_RX)]
    on_catecholaminergic = [m for m in meds
                            if any(c in m for c in CATECHOLAMINERGIC_RX)]
    return PatientContext(
        has_seizure_concern=has_seizure_concern,
        on_asm=on_asm,
        on_serotonergic=on_serotonergic,
        on_catecholaminergic=on_catecholaminergic,
    )


def _seizure_flag(iv: Intervention, ctx: PatientContext) -> SafetyFlag | None:
    if iv.seizure_risk == "raises":
        if ctx.has_seizure_concern and not ctx.on_asm:
            sev = Severity.HARD_BLOCK
            tail = "Defer until EEG capture and epilepsy clearance."
        else:
            sev = Severity.WARN
            tail = "Discuss with epilepsy team first."
        return SafetyFlag(
            severity=sev, axis="seizure",
            rationale=(f"{iv.name} is reported to lower seizure threshold. {tail}"),
        )
    if iv.seizure_risk == "mixed":
        return SafetyFlag(
            severity=Severity.CAUTION, axis="seizure",
            rationale=f"{iv.name} has mixed seizure-threshold signals — review primary literature.",
        )
    if iv.seizure_risk == "lowers" and ctx.has_seizure_concern:
        return SafetyFlag(
            severity=Severity.OK, axis="seizure",
            rationale=f"{iv.name} is associated with raised seizure threshold (favorable for this profile).",
        )
    return None


def _serotonergic_flag(iv: Intervention, ctx: PatientContext) -> SafetyFlag | None:
    if not ctx.on_serotonergic:
        return None
    rx_list = ", ".join(ctx.on_serotonergic)
    if iv.key in STRONG_SEROTONERGIC:
        return SafetyFlag(
            severity=Severity.HARD_BLOCK, axis="serotonergic",
            rationale=(f"{iv.name} is strongly serotonergic; coadministration with "
                       f"{rx_list} risks serotonin syndrome. Discontinuation/washout "
                       f"plus physician supervision would be prerequisites."),
        )
    for note in iv.interactions:
        nl = note.lower()
        if any(rx in nl for rx in SEROTONERGIC_RX):
            sev = (Severity.HARD_BLOCK
                   if "serotonin syndrome" in nl or "contraindicated" in nl
                   else Severity.CAUTION)
            return SafetyFlag(severity=sev, axis="serotonergic", rationale=note)
    return None


def _catecholaminergic_flag(iv: Intervention, ctx: PatientContext) -> SafetyFlag | None:
    if not ctx.on_catecholaminergic:
        return None
    rx_list = ", ".join(ctx.on_catecholaminergic)
    if iv.key in STRONG_CATECHOLAMINERGIC:
        return SafetyFlag(
            severity=Severity.WARN, axis="catecholaminergic",
            rationale=(f"{iv.name} stacks on baseline catecholaminergic load "
                       f"({rx_list}); monitor BP/HR. Catecholamine excess is "
                       f"independently pro-convulsant."),
        )
    for note in iv.interactions:
        nl = note.lower()
        if any(rx in nl for rx in CATECHOLAMINERGIC_RX):
            return SafetyFlag(severity=Severity.CAUTION,
                              axis="catecholaminergic", rationale=note)
    return None


def screen(intervention: Intervention,
           ctx: PatientContext | None = None) -> SafetyVerdict:
    ctx = ctx or derive_context()
    flags: list[SafetyFlag] = []
    for fn in (_seizure_flag, _serotonergic_flag, _catecholaminergic_flag):
        f = fn(intervention, ctx)
        if f is not None:
            flags.append(f)
    order = [Severity.OK, Severity.CAUTION, Severity.WARN, Severity.HARD_BLOCK]
    overall = max((f.severity for f in flags), key=order.index, default=Severity.OK)
    return SafetyVerdict(intervention_key=intervention.key,
                         overall=overall, flags=flags)


def screen_all() -> dict[str, SafetyVerdict]:
    ctx = derive_context()
    return {k: screen(iv, ctx) for k, iv in INTERVENTIONS_BY_KEY.items()}


if __name__ == "__main__":
    import json
    verdicts = screen_all()
    out = {k: {"overall": v.overall.value,
               "flags": [{"severity": f.severity.value, "axis": f.axis,
                          "rationale": f.rationale} for f in v.flags]}
           for k, v in verdicts.items()}
    print(json.dumps(out, indent=2))

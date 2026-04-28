"""
Per-intervention briefing generator. Output is markdown so it renders
cleanly in the UI and is also human-readable as a file.

A briefing has six sections:
  1. Verdict (safety + evidence summary)
  2. Why this is on the list (mechanism vs patient findings)
  3. Strongest evidence (top studies by quality * plausibility)
  4. Best objections (counter-evidence)
  5. Practical considerations (interactions, dosing literature, monitoring)
  6. Open questions

Generation is template-based with optional LLM polish via Ollama. The
template produces a usable briefing even with no LLM.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from app.db import connect
from app.ontology import INTERVENTIONS_BY_KEY, TARGETS_BY_KEY
from app.safety import screen
from app.seed import load as load_profile


def _top_studies(conn: sqlite3.Connection, intervention_key: str, k: int = 5) -> list[dict]:
    rows = conn.execute("""
        SELECT e.title, e.url, e.tier, e.study_type, e.published, e.source,
               eg.evidence_quality, eg.mechanistic_plausibility
        FROM evidence e JOIN evidence_grade eg USING (fingerprint)
        WHERE e.intervention_keys LIKE ?
        ORDER BY (eg.evidence_quality * eg.mechanistic_plausibility) DESC
        LIMIT ?
    """, (f'%"{intervention_key}"%', k)).fetchall()
    return [dict(r) for r in rows]


def _objections(conn: sqlite3.Connection, intervention_key: str, k: int = 3) -> list[dict]:
    """Best counter-evidence: high-quality + low-plausibility OR explicit
    'no benefit' phrasing in title."""
    rows = conn.execute("""
        SELECT e.title, e.url, e.tier, e.source, eg.evidence_quality,
               eg.mechanistic_plausibility
        FROM evidence e JOIN evidence_grade eg USING (fingerprint)
        WHERE e.intervention_keys LIKE ?
          AND eg.evidence_quality > 0.6
          AND (e.title LIKE '%no benefit%' OR e.title LIKE '%failed%'
               OR e.title LIKE '%negative%' OR e.title LIKE '%null%'
               OR e.title LIKE '%no effect%')
        LIMIT ?
    """, (f'%"{intervention_key}"%', k)).fetchall()
    return [dict(r) for r in rows]


def generate(intervention_key: str) -> str:
    iv = INTERVENTIONS_BY_KEY.get(intervention_key)
    if not iv:
        return f"# Unknown intervention: {intervention_key}"
    verdict = screen(iv)
    conn = connect()
    score_row = conn.execute(
        "SELECT * FROM intervention_score WHERE intervention_key = ?",
        (intervention_key,)).fetchone()
    top = _top_studies(conn, intervention_key)
    objections = _objections(conn, intervention_key)
    conn.close()

    targets_md = ", ".join(
        TARGETS_BY_KEY[tk].canonical for tk in iv.targets if tk in TARGETS_BY_KEY
    ) or "(unspecified)"

    flag_md = "\n".join(
        f"  - **{f.severity.value.upper()}** ({f.axis}): {f.rationale}"
        for f in verdict.flags
    ) or "  - No flags."

    studies_md = "\n".join(
        f"  - [{s['title']}]({s['url']}) — *{s['source']}*, "
        f"{s['study_type']}, q={s['evidence_quality']:.2f}, "
        f"p={s['mechanistic_plausibility']:.2f}"
        for s in top
    ) or "  - No retrieved evidence yet."

    obj_md = "\n".join(
        f"  - [{o['title']}]({o['url']}) — *{o['source']}*, q={o['evidence_quality']:.2f}"
        for o in objections
    ) or "  - No high-quality counter-evidence retrieved."

    score_md = (
        f"- N evidence: **{score_row['n_evidence']}**\n"
        f"- Mean evidence quality: **{score_row['mean_quality']:.2f}**\n"
        f"- Mean mechanistic plausibility: **{score_row['mean_plausibility']:.2f}**\n"
        if score_row else "- No score rolled up yet (run scheduler first).\n"
    )

    profile = load_profile()
    if profile.findings and not profile.findings[0].label.startswith("(example)"):
        anchor = "; ".join(f.label for f in profile.findings[:3])
    else:
        anchor = "synthetic example profile (drop documents into data/patient_corpus to anchor to a real profile)"

    meds_md = (", ".join(profile.medications)
               if profile.medications else "(none in profile)")

    return f"""# Briefing: {iv.name}

*Generated {datetime.now(timezone.utc).isoformat()} — anchored to: {anchor}.*

## 1. Verdict
- **Safety overall**: `{verdict.overall.value.upper()}`
{flag_md}

{score_md}

## 2. Why this is on the list
- Category: **{iv.category}** | Expected evidence tier: **{iv.expected_tier}**
- Mechanistic targets: {targets_md}
- Notes: {iv.notes or "—"}

## 3. Strongest evidence
{studies_md}

## 4. Best objections / counter-evidence
{obj_md}

## 5. Practical considerations
- Seizure-risk axis: **{iv.seizure_risk}**
- Known interaction notes: {", ".join(iv.interactions) if iv.interactions else "none encoded"}
- Patient meds in scope: {meds_md}

## 6. Open questions
- Does the strongest evidence actually study the chronicity stage in the patient's profile?
- Are dosing protocols compatible with the patient's current medication list?
- Is there a study that informs seizure-threshold risk if seizures are on the open-diagnoses list?
- Are there studies that match the specific anatomy/findings in this profile?

---
*This is research-platform output, not medical advice. Discuss with the treating neurologist before any change.*
"""


def generate_all() -> dict[str, str]:
    return {k: generate(k) for k in INTERVENTIONS_BY_KEY}


if __name__ == "__main__":
    import sys
    key = sys.argv[1] if len(sys.argv) > 1 else "lions_mane"
    print(generate(key))

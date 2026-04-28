"""Persistence helpers — Evidence/Grade/Score/Verdict upserts."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict

from app.connectors.base import Evidence
from app.grading import Grade
from app.safety import SafetyVerdict


def upsert_evidence(conn: sqlite3.Connection, e: Evidence) -> str:
    fp = e.fingerprint()
    conn.execute(
        """INSERT OR REPLACE INTO evidence
           (fingerprint, source, tier, url, title, abstract, published,
            authors, target_keys, intervention_keys, study_type,
            sample_size, raw_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (fp, e.source, e.tier, e.url, e.title, e.abstract,
         e.published.isoformat() if e.published else None,
         json.dumps(e.authors), json.dumps(e.target_keys),
         json.dumps(e.intervention_keys), e.study_type, e.sample_size,
         json.dumps(e.raw, default=str)),
    )
    return fp


def upsert_grade(conn: sqlite3.Connection, fingerprint: str, g: Grade) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO evidence_grade
           (fingerprint, evidence_quality, mechanistic_plausibility, rationale)
           VALUES (?,?,?,?)""",
        (fingerprint, g.evidence_quality, g.mechanistic_plausibility, g.rationale),
    )


def upsert_safety(conn: sqlite3.Connection, v: SafetyVerdict) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO safety_verdict
           (intervention_key, overall, flags_json) VALUES (?,?,?)""",
        (v.intervention_key, v.overall.value,
         json.dumps([{"severity": f.severity.value, "axis": f.axis,
                      "rationale": f.rationale} for f in v.flags])),
    )


def recompute_intervention_scores(conn: sqlite3.Connection) -> None:
    """Roll grades up to a per-intervention summary."""
    rows = conn.execute("""
        SELECT e.intervention_keys, eg.evidence_quality, eg.mechanistic_plausibility,
               e.fingerprint, e.title, e.url, e.tier, e.study_type
        FROM evidence e
        JOIN evidence_grade eg USING (fingerprint)
        WHERE e.intervention_keys != '[]'
    """).fetchall()
    by_iv: dict[str, list[dict]] = {}
    for r in rows:
        for ik in json.loads(r["intervention_keys"]):
            by_iv.setdefault(ik, []).append({
                "fingerprint": r["fingerprint"], "q": r["evidence_quality"],
                "p": r["mechanistic_plausibility"], "title": r["title"],
                "url": r["url"], "tier": r["tier"], "study_type": r["study_type"],
            })
    for ik, items in by_iv.items():
        n = len(items)
        mq = sum(i["q"] for i in items) / n
        mp = sum(i["p"] for i in items) / n
        top = sorted(items, key=lambda i: i["q"] * i["p"], reverse=True)[:5]
        conn.execute(
            """INSERT OR REPLACE INTO intervention_score
               (intervention_key, n_evidence, mean_quality, mean_plausibility, top_studies_json)
               VALUES (?,?,?,?,?)""",
            (ik, n, mq, mp, json.dumps(top)),
        )

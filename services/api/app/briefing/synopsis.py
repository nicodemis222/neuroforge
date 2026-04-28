"""
Cross-intervention synopsis — what changed, top-of-stack findings,
target-cluster patterns. Read by /api/synopsis.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from app.db import connect
from app.ontology import (INTERVENTIONS_BY_KEY, TARGETS_BY_KEY)


def _row(r: sqlite3.Row) -> dict:
    return dict(r)


def _top_interventions(conn: sqlite3.Connection, k: int = 8) -> list[dict]:
    rows = conn.execute("""
        SELECT intervention_key, n_evidence, mean_quality, mean_plausibility
        FROM intervention_score
        WHERE n_evidence > 0
        ORDER BY (mean_quality * mean_plausibility) DESC
        LIMIT ?
    """, (k,)).fetchall()
    out = []
    for r in rows:
        iv = INTERVENTIONS_BY_KEY.get(r["intervention_key"])
        out.append({
            "intervention_key": r["intervention_key"],
            "name": iv.name if iv else r["intervention_key"],
            "category": iv.category if iv else "?",
            "n_evidence": r["n_evidence"],
            "mean_quality": r["mean_quality"],
            "mean_plausibility": r["mean_plausibility"],
            "score": (r["mean_quality"] or 0) * (r["mean_plausibility"] or 0),
        })
    return out


def _recent_evidence(conn: sqlite3.Connection, hours: int = 24,
                     k: int = 12) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows = conn.execute("""
        SELECT e.title, e.url, e.tier, e.source, e.study_type, e.fetched_at,
               e.intervention_keys, eg.evidence_quality, eg.mechanistic_plausibility
        FROM evidence e LEFT JOIN evidence_grade eg USING (fingerprint)
        WHERE e.fetched_at > ?
        ORDER BY (eg.evidence_quality * eg.mechanistic_plausibility) DESC NULLS LAST,
                 e.fetched_at DESC
        LIMIT ?
    """, (cutoff, k)).fetchall()
    return [_row(r) for r in rows]


def _target_clusters(conn: sqlite3.Connection) -> list[dict]:
    """For each target, list seeded interventions that engage it, ranked by score.

    Highlights interventions that share mechanisms — useful for noticing
    'three different approaches converging on the same target'."""
    rows = conn.execute("""
        SELECT intervention_key, mean_quality, mean_plausibility
        FROM intervention_score
        WHERE n_evidence > 0
    """).fetchall()
    score_by_key = {r["intervention_key"]: (r["mean_quality"] or 0) *
                    (r["mean_plausibility"] or 0) for r in rows}

    by_target: dict[str, list[dict]] = {}
    for ivk, sc in score_by_key.items():
        iv = INTERVENTIONS_BY_KEY.get(ivk)
        if not iv:
            continue
        for tk in iv.targets:
            t = TARGETS_BY_KEY.get(tk)
            if not t:
                continue
            by_target.setdefault(tk, []).append({
                "intervention_key": ivk, "name": iv.name, "score": sc,
            })

    clusters = []
    for tk, members in by_target.items():
        if len(members) < 2:
            continue
        t = TARGETS_BY_KEY[tk]
        members.sort(key=lambda m: m["score"], reverse=True)
        clusters.append({
            "target_key": tk,
            "target": t.canonical,
            "patient_relevance": t.patient_relevance,
            "members": members[:5],
        })
    clusters.sort(key=lambda c: c["patient_relevance"], reverse=True)
    return clusters[:6]


def _safety_summary(conn: sqlite3.Connection) -> dict:
    rows = conn.execute("""
        SELECT overall, COUNT(*) AS n FROM safety_verdict GROUP BY overall
    """).fetchall()
    return {r["overall"]: r["n"] for r in rows}


def _coverage(conn: sqlite3.Connection) -> dict:
    n_total = len(INTERVENTIONS_BY_KEY)
    seeded = conn.execute(
        "SELECT COUNT(*) AS n FROM intervention_score WHERE n_evidence > 0"
    ).fetchone()
    n_seeded = seeded["n"] if seeded else 0
    n_evidence = conn.execute(
        "SELECT COUNT(*) AS n FROM evidence"
    ).fetchone()["n"]
    return {
        "interventions_total": n_total,
        "interventions_seeded": n_seeded,
        "evidence_rows": n_evidence,
    }


def generate() -> dict:
    conn = connect()
    try:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "coverage": _coverage(conn),
            "safety_distribution": _safety_summary(conn),
            "top_interventions": _top_interventions(conn),
            "recent_evidence": _recent_evidence(conn),
            "target_clusters": _target_clusters(conn),
        }
    finally:
        conn.close()

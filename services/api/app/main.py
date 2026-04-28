"""FastAPI app — research-platform backend."""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.briefing import generate as briefing_generate
from app.db import connect
from app.db.persist import upsert_safety
from app.ontology import INTERVENTIONS, INTERVENTIONS_BY_KEY, TARGETS
from app.safety import screen, screen_all
from app.scheduler import run_one_intervention, run_scheduler
from app.seed import load as load_profile
from app.routers import init_status, corpus, research

app = FastAPI(title="NEUROFORGE", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(init_status.router)
app.include_router(corpus.router)
app.include_router(research.router)


@app.on_event("startup")
async def _startup() -> None:
    conn = connect()
    for v in screen_all().values():
        upsert_safety(conn, v)
    conn.commit()
    conn.close()
    # Background scheduler — opt-in via env to avoid hammering on every dev reload.
    import os
    if os.environ.get("NEUROFORGE_SCHEDULER", "") == "1":
        asyncio.create_task(run_scheduler())


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "neuroforge"}


@app.get("/api/profile")
def profile() -> dict:
    p = load_profile()
    from dataclasses import asdict
    return asdict(p)


@app.get("/api/ontology/targets")
def list_targets() -> list[dict]:
    return [{"key": t.key, "canonical": t.canonical, "synonyms": list(t.synonyms),
             "mechanism": t.mechanism, "patient_relevance": t.patient_relevance,
             "notes": t.notes} for t in TARGETS]


@app.get("/api/ontology/interventions")
def list_interventions() -> list[dict]:
    """List interventions with live safety screen derived from the loaded
    profile. Safety is computed fresh per call so changes to the patient
    profile (via document ingest) reflect immediately."""
    verdicts = screen_all()
    out = []
    conn = connect()
    for iv in INTERVENTIONS:
        score = conn.execute(
            "SELECT * FROM intervention_score WHERE intervention_key = ?",
            (iv.key,)).fetchone()
        v = verdicts.get(iv.key)
        out.append({
            "key": iv.key, "name": iv.name, "category": iv.category,
            "targets": list(iv.targets), "expected_tier": iv.expected_tier,
            "seizure_risk": iv.seizure_risk,
            "interactions": list(iv.interactions),
            "notes": iv.notes,
            "n_evidence": score["n_evidence"] if score else 0,
            "mean_quality": score["mean_quality"] if score else None,
            "mean_plausibility": score["mean_plausibility"] if score else None,
            "safety_overall": v.overall.value if v else "ok",
            "safety_flags": [
                {"severity": f.severity.value, "axis": f.axis,
                 "rationale": f.rationale} for f in (v.flags if v else [])
            ],
        })
    conn.close()
    return out


@app.get("/api/intervention/{key}/evidence")
def intervention_evidence(key: str, limit: int = 50) -> list[dict]:
    if key not in INTERVENTIONS_BY_KEY:
        raise HTTPException(404)
    conn = connect()
    rows = conn.execute("""
        SELECT e.*, eg.evidence_quality, eg.mechanistic_plausibility
        FROM evidence e LEFT JOIN evidence_grade eg USING (fingerprint)
        WHERE e.intervention_keys LIKE ?
        ORDER BY (eg.evidence_quality * eg.mechanistic_plausibility) DESC NULLS LAST
        LIMIT ?
    """, (f'%"{key}"%', limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/intervention/{key}/briefing")
def briefing(key: str) -> dict:
    if key not in INTERVENTIONS_BY_KEY:
        raise HTTPException(404)
    return {"intervention_key": key, "markdown": briefing_generate(key)}


@app.post("/api/intervention/{key}/refresh")
async def refresh(key: str) -> dict:
    iv = INTERVENTIONS_BY_KEY.get(key)
    if not iv:
        raise HTTPException(404)
    asyncio.create_task(run_one_intervention(iv))
    return {"queued": key}


@app.get("/api/safety/{key}")
def safety(key: str) -> dict:
    iv = INTERVENTIONS_BY_KEY.get(key)
    if not iv:
        raise HTTPException(404)
    v = screen(iv)
    return {"intervention_key": key, "overall": v.overall.value,
            "flags": [{"severity": f.severity.value, "axis": f.axis,
                       "rationale": f.rationale} for f in v.flags]}

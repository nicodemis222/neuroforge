"""
Scheduler — adapted from deadstick. One async loop per (tier, intervention)
pair with jittered first-fire and per-loop locks.

For the MVP we use a flat loop set over interventions (cycling through
their target connections) on a slow cadence. The full deadstick-style
19-loop architecture is overkill at our scale; we emulate the most useful
properties (jitter, locking, polite pacing) without the operational tax.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone

from app.connectors import all_connectors
from app.db import connect
from app.db.persist import (recompute_intervention_scores, upsert_evidence,
                            upsert_grade, upsert_safety)
from app.grading import grade
from app.ontology import INTERVENTIONS, TARGETS_BY_KEY
from app.safety import screen_all
from app.seed import load as load_profile, patient_keywords

log = logging.getLogger("neuroforge.scheduler")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")


def build_query(intervention_name: str, target_terms: list[str],
                anchor_terms: list[str]) -> str:
    """Combine an intervention with its target + patient-anchor terms.

    The result is a single string (most APIs accept boolean OR via spaces
    or quoted phrases). We pick the top-N anchors to keep query length
    manageable across endpoints with strict limits."""
    targets_part = " OR ".join(f'"{t}"' for t in target_terms[:3])
    anchors_part = " OR ".join(f'"{t}"' for t in anchor_terms[:3])
    return f'"{intervention_name}" AND ({targets_part}) AND ({anchors_part})'


async def run_one_intervention(iv) -> None:
    profile = load_profile()
    anchors = patient_keywords(profile)
    # union of mechanism terms from this intervention's targets
    target_terms: list[str] = []
    for tk in iv.targets:
        t = TARGETS_BY_KEY.get(tk)
        if t:
            target_terms.append(t.canonical)
            target_terms.extend(t.synonyms[:2])
    query = build_query(iv.name, target_terms, anchors)
    log.info("[%s] querying with: %s", iv.key, query[:160])
    conn = connect()
    n_total = 0
    for connector in all_connectors():
        try:
            async for ev in connector.search(
                query, target_key=(iv.targets[0] if iv.targets else None),
                intervention_key=iv.key, limit=15,
            ):
                fp = upsert_evidence(conn, ev)
                g = grade(ev, profile)
                upsert_grade(conn, fp, g)
                n_total += 1
        except Exception as e:
            log.warning("[%s] %s failed: %s", iv.key, connector.key, e)
    conn.commit()
    conn.close()
    log.info("[%s] persisted %d evidence rows", iv.key, n_total)


async def safety_loop() -> None:
    while True:
        conn = connect()
        for v in screen_all().values():
            upsert_safety(conn, v)
        conn.commit()
        conn.close()
        await asyncio.sleep(3600)  # hourly is plenty


async def rollup_loop() -> None:
    while True:
        await asyncio.sleep(180)
        conn = connect()
        try:
            recompute_intervention_scores(conn)
            conn.commit()
        finally:
            conn.close()


async def intervention_loop() -> None:
    """Cycle through every intervention with jittered cadence."""
    interval_seconds = 60 * 60 * 6  # 6h per intervention
    interventions = list(INTERVENTIONS)
    random.shuffle(interventions)
    while True:
        for iv in interventions:
            jitter = random.uniform(0, 60)
            await asyncio.sleep(jitter)
            try:
                await run_one_intervention(iv)
            except Exception as e:
                log.exception("[%s] loop error: %s", iv.key, e)
            await asyncio.sleep(interval_seconds / max(1, len(interventions)))


async def run_scheduler() -> None:
    log.info("neuroforge scheduler starting at %s", datetime.now(timezone.utc).isoformat())
    await asyncio.gather(safety_loop(), rollup_loop(), intervention_loop())


if __name__ == "__main__":
    asyncio.run(run_scheduler())

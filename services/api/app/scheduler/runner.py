"""
Scheduler with telemetry. Adapted from deadstick.

Three concurrent loops:
  1. intervention_loop  — cycles through interventions running connector sweeps
  2. safety_loop        — recomputes per-intervention safety verdicts hourly
  3. rollup_loop        — re-aggregates intervention scores every 3 minutes

Every state transition + connector call is logged to app.scheduler.telemetry.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone

from app.connectors import all_connectors
from app.db import connect
from app.db.persist import (recompute_intervention_scores, upsert_evidence,
                            upsert_grade, upsert_safety)
from app.grading import grade
from app.ontology import INTERVENTIONS, INTERVENTIONS_BY_KEY, TARGETS_BY_KEY
from app.safety import screen_all
from app.seed import load as load_profile, patient_keywords
from app.scheduler.telemetry import telemetry

log = logging.getLogger("neuroforge.scheduler")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")


def build_query(intervention_name: str, target_terms: list[str],
                anchor_terms: list[str]) -> str:
    targets_part = " OR ".join(f'"{t}"' for t in target_terms[:3])
    anchors_part = " OR ".join(f'"{t}"' for t in anchor_terms[:3])
    return f'"{intervention_name}" AND ({targets_part}) AND ({anchors_part})'


async def run_one_intervention(iv) -> None:
    profile = load_profile()
    anchors = patient_keywords(profile)
    target_terms: list[str] = []
    for tk in iv.targets:
        t = TARGETS_BY_KEY.get(tk)
        if t:
            target_terms.append(t.canonical)
            target_terms.extend(t.synonyms[:2])
    query = build_query(iv.name, target_terms, anchors)

    telemetry.update_loop("intervention",
                          status="running",
                          last_intervention=iv.key,
                          last_tick=datetime.now(timezone.utc))
    telemetry.log("tick_start", loop="intervention",
                  intervention=iv.key, message=f"query: {query[:120]}")
    log.info("[%s] querying with: %s", iv.key, query[:160])

    conn = connect()
    n_total = 0
    for connector in all_connectors():
        telemetry.update_loop("intervention", last_connector=connector.key)
        try:
            count = 0
            async for ev in connector.search(
                query, target_key=(iv.targets[0] if iv.targets else None),
                intervention_key=iv.key, limit=15,
            ):
                fp = upsert_evidence(conn, ev)
                g = grade(ev, profile)
                upsert_grade(conn, fp, g)
                count += 1
                n_total += 1
            telemetry.log("connector", loop="intervention",
                          intervention=iv.key, connector=connector.key,
                          count=count, message=f"{count} rows")
        except Exception as e:
            telemetry.log("error", loop="intervention",
                          intervention=iv.key, connector=connector.key,
                          message=str(e))
            log.warning("[%s] %s failed: %s", iv.key, connector.key, e)
    conn.commit()
    conn.close()

    ls = telemetry.ensure_loop("intervention")
    telemetry.update_loop("intervention",
                          last_result_count=n_total,
                          total_ticks=ls.total_ticks + 1,
                          total_evidence_persisted=ls.total_evidence_persisted + n_total,
                          status="sleeping")
    telemetry.log("tick_end", loop="intervention", intervention=iv.key,
                  count=n_total, message=f"persisted {n_total} rows")
    log.info("[%s] persisted %d evidence rows", iv.key, n_total)


async def safety_loop() -> None:
    while True:
        telemetry.update_loop("safety", status="running",
                              last_tick=datetime.now(timezone.utc))
        telemetry.log("tick_start", loop="safety", message="rescreening interventions")
        try:
            conn = connect()
            n = 0
            for v in screen_all().values():
                upsert_safety(conn, v)
                n += 1
            conn.commit()
            conn.close()
            ls = telemetry.ensure_loop("safety")
            telemetry.update_loop("safety", status="sleeping",
                                  last_result_count=n,
                                  next_tick=datetime.now(timezone.utc) + timedelta(seconds=3600),
                                  total_ticks=ls.total_ticks + 1)
            telemetry.log("tick_end", loop="safety", count=n,
                          message=f"rescreened {n} interventions")
        except Exception as e:
            telemetry.update_loop("safety", status="error", last_error=str(e))
            telemetry.log("error", loop="safety", message=str(e))
        await asyncio.sleep(3600)


async def rollup_loop() -> None:
    while True:
        await asyncio.sleep(180)
        telemetry.update_loop("rollup", status="running",
                              last_tick=datetime.now(timezone.utc))
        telemetry.log("tick_start", loop="rollup", message="recomputing scores")
        try:
            conn = connect()
            recompute_intervention_scores(conn)
            conn.commit()
            conn.close()
            ls = telemetry.ensure_loop("rollup")
            telemetry.update_loop("rollup", status="sleeping",
                                  total_ticks=ls.total_ticks + 1,
                                  next_tick=datetime.now(timezone.utc) + timedelta(seconds=180))
            telemetry.log("tick_end", loop="rollup", message="scores updated")
        except Exception as e:
            telemetry.update_loop("rollup", status="error", last_error=str(e))
            telemetry.log("error", loop="rollup", message=str(e))


async def intervention_loop() -> None:
    interval_seconds = 60 * 60 * 6  # 6h spread across all interventions
    interventions = list(INTERVENTIONS)
    random.shuffle(interventions)
    per = interval_seconds / max(1, len(interventions))
    while True:
        telemetry.set_queue([iv.key for iv in interventions])
        for i, iv in enumerate(interventions):
            jitter = random.uniform(0, 30)
            telemetry.update_loop("intervention", status="sleeping",
                                  next_tick=datetime.now(timezone.utc) + timedelta(seconds=jitter))
            await asyncio.sleep(jitter)
            try:
                await run_one_intervention(iv)
            except Exception as e:
                telemetry.update_loop("intervention", status="error", last_error=str(e))
                telemetry.log("error", loop="intervention",
                              intervention=iv.key, message=str(e))
                log.exception("[%s] loop error: %s", iv.key, e)
            # Move processed item to end of visible queue
            telemetry.set_queue([j.key for j in interventions[i+1:]] + [j.key for j in interventions[:i+1]])
            telemetry.update_loop("intervention", status="sleeping",
                                  next_tick=datetime.now(timezone.utc) + timedelta(seconds=per))
            await asyncio.sleep(per)


async def run_scheduler() -> None:
    log.info("neuroforge scheduler starting at %s", datetime.now(timezone.utc).isoformat())
    telemetry.log("scheduled", loop="scheduler", message="boot")
    await asyncio.gather(safety_loop(), rollup_loop(), intervention_loop())


if __name__ == "__main__":
    asyncio.run(run_scheduler())

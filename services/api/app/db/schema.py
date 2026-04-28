"""
SQLite-by-default persistence. We use SQLite for local-first ops; the
schema is Postgres-compatible so future migration is mechanical.

Tables:
  evidence            — every retrieved record (deduped by fingerprint)
  evidence_grade      — paired grade per evidence
  intervention_score  — rolled-up score per intervention (recomputed nightly)
  safety_verdict      — current verdict per intervention
  briefing            — generated markdown briefings

The schema bootstrap runs at startup; no Alembic for the MVP.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent.parent / "data" / "neuroforge.db"

DDL = """
CREATE TABLE IF NOT EXISTS evidence (
    fingerprint   TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    tier          TEXT NOT NULL,
    url           TEXT,
    title         TEXT,
    abstract      TEXT,
    published     TEXT,
    authors       TEXT,
    target_keys   TEXT,
    intervention_keys TEXT,
    study_type    TEXT,
    sample_size   INTEGER,
    raw_json      TEXT,
    fetched_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evidence_tier ON evidence(tier);
CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence(source);

CREATE TABLE IF NOT EXISTS evidence_grade (
    fingerprint              TEXT PRIMARY KEY REFERENCES evidence(fingerprint),
    evidence_quality         REAL NOT NULL,
    mechanistic_plausibility REAL NOT NULL,
    rationale                TEXT,
    graded_at                TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS intervention_score (
    intervention_key TEXT PRIMARY KEY,
    n_evidence       INTEGER,
    mean_quality     REAL,
    mean_plausibility REAL,
    top_studies_json TEXT,
    updated_at       TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS safety_verdict (
    intervention_key TEXT PRIMARY KEY,
    overall          TEXT,
    flags_json       TEXT,
    updated_at       TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS briefing (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    intervention_key TEXT,
    target_key   TEXT,
    markdown     TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(DDL)
    return conn

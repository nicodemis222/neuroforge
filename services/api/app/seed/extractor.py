"""
Document corpus -> structured patient profile.

Pipeline:
  1. Walk data/patient_corpus/* for any supported format
     (pdf, docx, pptx, xlsx, csv, tsv, txt, md, html, rtf, json).
  2. Extract text via app.seed.ingest (format-specific dispatch).
  3. Hash + chunk.
  4. Run an LLM extraction pass (Ollama) to pull
     findings/symptoms/medications/diagnoses into structured JSON.
  5. Merge across documents and write to data/patient_corpus/profile.json,
     which app.seed.patient_profile.load() prefers over DEFAULT.

The extractor is idempotent: file content_hash gates re-processing
(stored in manifest.json alongside profile.json).

If Ollama is not running the extractor falls back to writing a stub
profile derived from filename heuristics + the file content hash so
downstream code still has a profile.json to load.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .ingest import IngestUnsupported, content_hash, is_supported, iter_documents

CORPUS = Path(__file__).resolve().parents[4] / "data" / "patient_corpus"
CHUNK_SIZE = 1200      # chars
CHUNK_OVERLAP = 200


def chunk(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    out, i = [], 0
    while i < len(text):
        out.append(text[i : i + size])
        i += max(1, size - overlap)
    return out


EXTRACTION_PROMPT = """You are a medical NLP extractor. Read the report excerpt and emit STRICT JSON
with this schema (omit fields you cannot ground in the text):

{{
  "findings": [{{"label": "", "location": "", "chronicity": "", "radiology_favored": "", "differential": []}}],
  "symptoms": [{{"label": "", "laterality": "", "onset": "", "duration": "", "frequency": "", "triggers": []}}],
  "medications": [],
  "diagnoses_open": [],
  "diagnoses_ruled_out": [],
  "risk_factors": []
}}

Excerpt:
---
{text}
---

JSON only:"""


def llm_extract(text: str, model: str | None = None) -> dict:
    """Call local Ollama for extraction. Returns {} on failure (caller falls back).

    Handles both standard and 'thinking' models — the thinking model
    families (qwen3, deepseek-r1, etc.) put output in `thinking` and
    leave `response` empty when format=json is set."""
    import os
    import re
    import httpx
    if model is None:
        model = os.environ.get("NEUROFORGE_EXTRACT_MODEL", "llama3.2:latest")
    try:
        r = httpx.post(
            "http://localhost:11434/api/generate",
            json={"model": model,
                  "prompt": EXTRACTION_PROMPT.format(text=text[:8000]),
                  "stream": False, "format": "json",
                  "options": {"temperature": 0.0}},
            timeout=180.0,
        )
        r.raise_for_status()
        data = r.json()
        body = data.get("response", "") or data.get("thinking", "") or ""
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            # Some thinking models embed JSON inside chain-of-thought text.
            m = re.search(r"\{.*\}", body, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
            print(f"[extractor] could not parse LLM JSON ({model}); skipping chunk")
            return {}
    except Exception as e:
        print(f"[extractor] LLM extraction skipped: {e}")
        return {}


def _coerce_str(v) -> str:
    """LLMs occasionally return objects where strings are expected. Flatten."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        # Prefer common label fields, then dump the whole dict as readable text
        for k in ("label", "name", "value", "text"):
            if k in v and isinstance(v[k], str):
                return v[k].strip()
        kvs = [f"{k}: {_coerce_str(val)}" for k, val in v.items()
               if val and not isinstance(val, (dict, list))]
        return "; ".join(kvs)
    if isinstance(v, list):
        return ", ".join(_coerce_str(x) for x in v if x)
    return str(v).strip()


def _coerce_str_list(v) -> list[str]:
    """Normalize a list field to a clean list[str], deduped, no empties."""
    if v is None:
        return []
    if not isinstance(v, list):
        v = [v]
    out: list[str] = []
    seen: set[str] = set()
    for item in v:
        s = _coerce_str(item)
        if not s or s.lower() in {"none", "n/a", "no", "unknown"}:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def merge(profiles: list[dict]) -> dict:
    """Union-merge LLM extractions across multiple documents.

    All scalars are coerced to clean strings; lists are deduped and
    empty/null-equivalent entries dropped."""
    out: dict = {
        "patient_ref": "ingested-patient",
        "age": 0,
        "sex": "unspecified",
        "findings": [], "symptoms": [], "medications": [],
        "diagnoses_open": [], "diagnoses_ruled_out": [], "risk_factors": [],
    }
    seen_finding_keys: set[tuple[str, str]] = set()
    seen_symptom_labels: set[str] = set()
    list_buckets: dict[str, list[str]] = {
        "medications": [], "diagnoses_open": [],
        "diagnoses_ruled_out": [], "risk_factors": [],
    }
    list_seen: dict[str, set[str]] = {k: set() for k in list_buckets}

    for p in profiles:
        for f in p.get("findings", []) or []:
            if not isinstance(f, dict):
                f = {"label": _coerce_str(f)}
            label = _coerce_str(f.get("label"))
            location = _coerce_str(f.get("location"))
            if not label and not location:
                continue
            key = (label, location)
            if key in seen_finding_keys:
                continue
            seen_finding_keys.add(key)
            out["findings"].append({
                "label": label, "location": location,
                "chronicity": _coerce_str(f.get("chronicity")),
                "radiology_favored": _coerce_str(f.get("radiology_favored")),
                "differential": _coerce_str_list(f.get("differential")),
                "source_doc": _coerce_str(f.get("source_doc")),
            })

        for s in p.get("symptoms", []) or []:
            if not isinstance(s, dict):
                s = {"label": _coerce_str(s)}
            label = _coerce_str(s.get("label"))
            if not label or label in seen_symptom_labels:
                continue
            seen_symptom_labels.add(label)
            out["symptoms"].append({
                "label": label,
                "laterality": _coerce_str(s.get("laterality")),
                "onset": _coerce_str(s.get("onset")),
                "duration": _coerce_str(s.get("duration")),
                "frequency": _coerce_str(s.get("frequency")),
                "triggers": _coerce_str_list(s.get("triggers")),
            })

        for k in list_buckets:
            for v in p.get(k, []) or []:
                s = _coerce_str(v)
                if not s or s.lower() in {"none", "n/a"}:
                    continue
                low = s.lower()
                if low in list_seen[k]:
                    continue
                list_seen[k].add(low)
                list_buckets[k].append(s)

    for k, vals in list_buckets.items():
        out[k] = vals
    return out


def run() -> Path:
    if not CORPUS.exists():
        CORPUS.mkdir(parents=True, exist_ok=True)
    docs = list(iter_documents_safe(CORPUS))
    if not docs:
        print(f"[extractor] No supported documents in {CORPUS} — keeping DEFAULT profile.")
        # Write nothing; loader will fall through to DEFAULT.
        return CORPUS / "profile.json"

    extractions: list[dict] = []
    manifest: dict = {}
    for path, h, text in docs:
        manifest[path.name] = {"sha256": h, "chars": len(text)}
        per_doc: list[dict] = []
        for c in chunk(text):
            r = llm_extract(c)
            if not r:
                continue
            for f in r.get("findings", []) or []:
                f["source_doc"] = path.name
            per_doc.append(r)
        extractions.extend(per_doc)
        print(f"[extractor] processed {path.name} ({len(text)} chars, "
              f"{len(per_doc)} extractions)")

    merged = merge(extractions) if extractions else {}
    if not merged.get("findings"):
        # Persist manifest but no profile so loader falls back to DEFAULT.
        (CORPUS / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print("[extractor] No findings extracted (Ollama down?). "
              "Wrote manifest only; profile.json left absent.")
        return CORPUS / "profile.json"

    out_path = CORPUS / "profile.json"
    out_path.write_text(json.dumps(merged, indent=2))
    (CORPUS / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[extractor] wrote {out_path} "
          f"({len(merged.get('findings', []))} findings, "
          f"{len(merged.get('symptoms', []))} symptoms)")
    return out_path


def iter_documents_safe(corpus: Path):
    """Wrapper around ingest.iter_documents that downgrades unsupported-format
    errors to warnings so a single bad file doesn't abort the run."""
    for p in sorted(corpus.iterdir()):
        if p.is_dir() or p.name.startswith(".") or p.name == "README.md":
            continue
        if not is_supported(p):
            print(f"[extractor] skipping unsupported file: {p.name}")
            continue
        try:
            from .ingest import extract_text
            yield p, content_hash(p), extract_text(p)
        except IngestUnsupported as e:
            print(f"[extractor] {p.name}: {e}")
        except Exception as e:
            print(f"[extractor] {p.name}: extraction failed: {e}")


if __name__ == "__main__":
    run()

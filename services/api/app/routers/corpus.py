"""
/api/corpus/* — manage the patient document corpus from the UI.

  GET    /api/corpus           list current files + supported formats
  POST   /api/corpus/upload    multipart upload one or more files
  DELETE /api/corpus/{name}    remove a file
  POST   /api/corpus/extract   re-run extractor.run() (background)

All operations are local-only — files live under data/patient_corpus/.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from app.seed.ingest import SUPPORTED_EXTS, content_hash, is_supported

router = APIRouter(prefix="/api/corpus", tags=["corpus"])

CORPUS = Path(__file__).resolve().parents[4] / "data" / "patient_corpus"


def _safe_name(name: str) -> str:
    """Reject path traversal; keep only the basename."""
    return Path(name).name


@router.get("")
def list_corpus() -> dict:
    CORPUS.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(CORPUS.iterdir()):
        if p.is_dir() or p.name.startswith(".") or p.name == "README.md":
            continue
        items.append({
            "name": p.name,
            "size_bytes": p.stat().st_size,
            "supported": is_supported(p),
            "ext": p.suffix.lower(),
        })
    return {"files": items, "supported_extensions": sorted(SUPPORTED_EXTS)}


@router.post("/upload")
async def upload(files: list[UploadFile] = File(...)) -> dict:
    CORPUS.mkdir(parents=True, exist_ok=True)
    saved = []
    rejected = []
    for f in files:
        name = _safe_name(f.filename or "")
        if not name:
            rejected.append({"name": "(empty)", "reason": "no filename"})
            continue
        ext = Path(name).suffix.lower()
        if ext not in SUPPORTED_EXTS:
            rejected.append({"name": name, "reason": f"unsupported ext '{ext}'"})
            continue
        target = CORPUS / name
        data = await f.read()
        target.write_bytes(data)
        saved.append({"name": name, "size_bytes": len(data),
                      "sha256": content_hash(target)})
    return {"saved": saved, "rejected": rejected}


@router.delete("/{name}")
def delete_file(name: str) -> dict:
    safe = _safe_name(name)
    p = CORPUS / safe
    if not p.exists() or p.is_dir():
        raise HTTPException(404, f"no such file: {safe}")
    p.unlink()
    return {"deleted": safe}


@router.post("/extract")
async def trigger_extract() -> JSONResponse:
    """Run the extractor in a background thread.

    Returns immediately; the UI should poll /api/profile to see new
    findings appear once extraction completes.
    """
    from app.seed.extractor import run

    async def _go():
        await asyncio.to_thread(run)

    asyncio.create_task(_go())
    return JSONResponse({"queued": True})

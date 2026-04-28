"""
/api/init/* — used by the Next.js init screen to:
  - check current readiness (status)
  - stream init.py output as Server-Sent Events (run)

The init endpoint runs scripts/init.py as a subprocess in --json mode and
forwards each JSON line as an SSE 'message' event.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/init", tags=["init"])

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
INIT_SCRIPT = ROOT / "scripts" / "init.py"
CORPUS_DIR = ROOT / "data" / "patient_corpus"
DB_PATH = ROOT / "data" / "neuroforge.db"
WEB_NM = ROOT / "web" / "node_modules"


@router.get("/status")
def status() -> dict:
    """Snapshot of readiness — fast, no installs, no network."""
    import os
    py_v = sys.version_info
    py_ok = (py_v.major, py_v.minor) >= (3, 11)
    scheduler_on = os.environ.get("NEUROFORGE_SCHEDULER", "") == "1"
    py_deps_ok = True
    for mod in ("fastapi", "uvicorn", "httpx", "pypdf", "feedparser"):
        try:
            __import__(mod)
        except ImportError:
            py_deps_ok = False
            break
    pdfs = list(CORPUS_DIR.glob("*.pdf")) if CORPUS_DIR.exists() else []
    node_ok = shutil.which("node") is not None
    npm_ok = shutil.which("npm") is not None
    web_ok = WEB_NM.exists()

    ollama_ok = False
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1) as r:
            r.read()
        ollama_ok = True
    except Exception:
        pass

    ready = py_ok and py_deps_ok and DB_PATH.exists()
    return {
        "ready": ready,
        "platform": sys.platform,
        "scheduler_on": scheduler_on,
        "python": {"version": f"{py_v.major}.{py_v.minor}.{py_v.micro}",
                   "ok": py_ok},
        "py_deps_ok": py_deps_ok,
        "node_ok": node_ok,
        "npm_ok": npm_ok,
        "web_deps_ok": web_ok,
        "db_ok": DB_PATH.exists(),
        "corpus_pdf_count": len(pdfs),
        "corpus_pdfs": [p.name for p in pdfs],
        "ollama_ok": ollama_ok,
        "init_script": str(INIT_SCRIPT),
    }


async def _stream_init(no_install: bool) -> "asyncio.StreamReader":
    args = [sys.executable, str(INIT_SCRIPT), "--json"]
    if no_install:
        args.append("--no-install")
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        cwd=str(ROOT),
    )
    return proc


@router.get("/run")
async def run(no_install: bool = False) -> StreamingResponse:
    """Stream init.py output as Server-Sent Events.

    Frontend usage:
      const es = new EventSource('/api/init/run');
      es.onmessage = (e) => append(JSON.parse(e.data));
    """
    async def gen():
        proc = await _stream_init(no_install=no_install)
        assert proc.stdout is not None
        try:
            async for raw in proc.stdout:
                line = raw.decode("utf-8", errors="replace").rstrip()
                if not line:
                    continue
                # Each init.py line is already a JSON object — forward as SSE.
                try:
                    json.loads(line)
                    yield f"data: {line}\n\n"
                except json.JSONDecodeError:
                    yield f"data: {json.dumps({'step':'log','status':'log','message':line})}\n\n"
            await proc.wait()
            yield f"data: {json.dumps({'step':'exit','status':'ok' if proc.returncode==0 else 'error','message':f'exit code {proc.returncode}'})}\n\n"
        finally:
            if proc.returncode is None:
                proc.kill()
    return StreamingResponse(gen(), media_type="text/event-stream")

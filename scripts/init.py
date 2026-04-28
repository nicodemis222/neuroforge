"""
NEUROFORGE cross-platform initializer.

Runs the same on macOS / Linux / Windows. Streams progress as JSON lines
to stdout when invoked with `--json` (the API/UI consumes that),
otherwise prints human-readable lines.

Checks performed, in order:
  1. Python >= 3.11
  2. pip available
  3. Python deps (fastapi, uvicorn, httpx, pypdf, feedparser) — install if missing
  4. Node.js >= 18 (warn-only — only required for the web UI)
  5. npm available
  6. Web deps (web/node_modules) — install if missing
  7. Patient corpus PDFs present in data/patient_corpus/
  8. SQLite DB schema bootstrapped at data/neuroforge.db
  9. Ollama reachability at http://localhost:11434 (warn-only)
 10. Network reachability for at least one T1 source (PubMed)

Each step emits a {step, status, message} record. Status is one of
'ok' | 'warn' | 'error' | 'installing'. The script exits 0 if no
'error' was emitted, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_DIR = ROOT / "services" / "api"
WEB_DIR = ROOT / "web"
DATA_DIR = ROOT / "data"
CORPUS_DIR = DATA_DIR / "patient_corpus"
DB_PATH = DATA_DIR / "neuroforge.db"

REQUIRED_PY = (3, 11)
REQUIRED_NODE_MAJOR = 18
PY_DEPS = ["fastapi", "uvicorn", "httpx", "pypdf", "feedparser"]


def emit(step: str, status: str, message: str, *, json_mode: bool) -> None:
    payload = {"step": step, "status": status, "message": message,
               "ts": time.time()}
    if json_mode:
        print(json.dumps(payload), flush=True)
    else:
        marker = {"ok": "[OK]", "warn": "[WARN]", "error": "[ERR]",
                  "installing": "[..]"}.get(status, "[..]")
        print(f"{marker} {step}: {message}", flush=True)


def run_cmd(cmd: list[str], cwd: Path | None = None,
            timeout: int = 600) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None,
            capture_output=True, text=True, timeout=timeout,
            shell=(platform.system() == "Windows" and cmd[0] in ("npm", "node")),
        )
        return proc.returncode, (proc.stdout + proc.stderr)[-2000:]
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def check_python(*, json_mode: bool) -> bool:
    v = sys.version_info
    if (v.major, v.minor) < REQUIRED_PY:
        emit("python", "error",
             f"Python {v.major}.{v.minor} found; need >= {REQUIRED_PY[0]}.{REQUIRED_PY[1]}",
             json_mode=json_mode)
        return False
    emit("python", "ok", f"Python {v.major}.{v.minor}.{v.micro}", json_mode=json_mode)
    return True


def check_pip(*, json_mode: bool) -> bool:
    rc, out = run_cmd([sys.executable, "-m", "pip", "--version"])
    if rc != 0:
        emit("pip", "error", f"pip not available: {out}", json_mode=json_mode)
        return False
    emit("pip", "ok", out.strip().splitlines()[0] if out.strip() else "pip ok",
         json_mode=json_mode)
    return True


def check_py_deps(*, json_mode: bool, install: bool = True) -> bool:
    missing: list[str] = []
    for mod in PY_DEPS:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if not missing:
        emit("py_deps", "ok", "all Python deps present", json_mode=json_mode)
        return True
    if not install:
        emit("py_deps", "error", f"missing: {', '.join(missing)}", json_mode=json_mode)
        return False
    emit("py_deps", "installing",
         f"installing: pip install -e {API_DIR}",
         json_mode=json_mode)
    rc, out = run_cmd([sys.executable, "-m", "pip", "install", "-e", str(API_DIR)],
                      timeout=900)
    if rc != 0:
        emit("py_deps", "error", f"pip install failed: {out}", json_mode=json_mode)
        return False
    # Re-verify
    still_missing = []
    for mod in PY_DEPS:
        try:
            __import__(mod)
        except ImportError:
            still_missing.append(mod)
    if still_missing:
        emit("py_deps", "error", f"still missing after install: {still_missing}",
             json_mode=json_mode)
        return False
    emit("py_deps", "ok", "Python deps installed", json_mode=json_mode)
    return True


def check_node(*, json_mode: bool) -> bool:
    if shutil.which("node") is None:
        emit("node", "warn",
             "Node.js not found — required only for the web UI. "
             "Install from https://nodejs.org/ (LTS) and re-run init.",
             json_mode=json_mode)
        return False
    rc, out = run_cmd(["node", "--version"])
    if rc != 0:
        emit("node", "warn", f"node failed: {out}", json_mode=json_mode)
        return False
    ver = out.strip().lstrip("v").split(".")
    try:
        major = int(ver[0])
    except (ValueError, IndexError):
        major = 0
    if major < REQUIRED_NODE_MAJOR:
        emit("node", "warn",
             f"Node {out.strip()} found; UI needs >= {REQUIRED_NODE_MAJOR}",
             json_mode=json_mode)
        return False
    emit("node", "ok", f"Node {out.strip()}", json_mode=json_mode)
    return True


def check_npm(*, json_mode: bool) -> bool:
    if shutil.which("npm") is None:
        emit("npm", "warn", "npm not found", json_mode=json_mode)
        return False
    rc, out = run_cmd(["npm", "--version"])
    if rc != 0:
        emit("npm", "warn", f"npm failed: {out}", json_mode=json_mode)
        return False
    emit("npm", "ok", f"npm {out.strip()}", json_mode=json_mode)
    return True


def check_web_deps(*, json_mode: bool, install: bool = True) -> bool:
    if not WEB_DIR.exists():
        emit("web_deps", "warn", "web/ directory missing", json_mode=json_mode)
        return False
    if (WEB_DIR / "node_modules").exists():
        emit("web_deps", "ok", "node_modules present", json_mode=json_mode)
        return True
    if not install or shutil.which("npm") is None:
        emit("web_deps", "warn", "node_modules missing; run `npm install` in web/",
             json_mode=json_mode)
        return False
    emit("web_deps", "installing", "running `npm install` in web/ (60-180s)…",
         json_mode=json_mode)
    rc, out = run_cmd(["npm", "install", "--no-audit", "--no-fund"], cwd=WEB_DIR,
                      timeout=900)
    if rc != 0:
        emit("web_deps", "error", f"npm install failed: {out}", json_mode=json_mode)
        return False
    emit("web_deps", "ok", "web deps installed", json_mode=json_mode)
    return True


def check_corpus(*, json_mode: bool) -> bool:
    if not CORPUS_DIR.exists():
        CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = list(CORPUS_DIR.glob("*.pdf"))
    if not pdfs:
        emit("corpus", "warn",
             f"no PDFs in {CORPUS_DIR}. Drop reports there, then re-run init "
             "or use scripts/seed.py to extract.",
             json_mode=json_mode)
        return False
    emit("corpus", "ok", f"{len(pdfs)} PDF(s) in patient corpus",
         json_mode=json_mode)
    return True


def check_db(*, json_mode: bool) -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(API_DIR))
    try:
        from app.db import connect  # type: ignore
        conn = connect()
        conn.execute("SELECT 1")
        conn.close()
    except Exception as e:
        emit("db", "error", f"DB bootstrap failed: {e}", json_mode=json_mode)
        return False
    emit("db", "ok", f"SQLite ready at {DB_PATH}", json_mode=json_mode)
    return True


def check_ollama(*, json_mode: bool) -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            r.read()
        emit("ollama", "ok", "Ollama reachable on localhost:11434",
             json_mode=json_mode)
        return True
    except Exception:
        emit("ollama", "warn",
             "Ollama not running (optional — needed for PDF extraction). "
             "Install from https://ollama.com/ and `ollama pull qwen2.5:7b`.",
             json_mode=json_mode)
        return False


def check_network(*, json_mode: bool) -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi?db=pubmed",
            timeout=8,
        ) as r:
            r.read(64)
        emit("network", "ok", "PubMed reachable", json_mode=json_mode)
        return True
    except Exception as e:
        emit("network", "warn", f"PubMed unreachable: {e}", json_mode=json_mode)
        return False


def check_safety(*, json_mode: bool) -> bool:
    """Verify the safety module loads and produces verdicts."""
    sys.path.insert(0, str(API_DIR))
    try:
        from app.safety import screen_all  # type: ignore
        verdicts = screen_all()
        blocks = [k for k, v in verdicts.items() if v.overall.value == "hard_block"]
        emit("safety", "ok",
             f"{len(verdicts)} interventions screened; "
             f"{len(blocks)} hard-blocked: {', '.join(blocks) or '(none)'}",
             json_mode=json_mode)
        return True
    except Exception as e:
        emit("safety", "error", f"safety module failed: {e}", json_mode=json_mode)
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON-lines for the UI to consume.")
    parser.add_argument("--no-install", action="store_true",
                        help="Check only; do not install missing deps.")
    args = parser.parse_args()
    json_mode = args.json
    install = not args.no_install

    emit("start", "ok",
         f"NEUROFORGE init starting on {platform.system()} {platform.release()}",
         json_mode=json_mode)

    had_error = False
    steps = [
        ("python",   lambda: check_python(json_mode=json_mode)),
        ("pip",      lambda: check_pip(json_mode=json_mode)),
        ("py_deps",  lambda: check_py_deps(json_mode=json_mode, install=install)),
        ("node",     lambda: check_node(json_mode=json_mode)),
        ("npm",      lambda: check_npm(json_mode=json_mode)),
        ("web_deps", lambda: check_web_deps(json_mode=json_mode, install=install)),
        ("corpus",   lambda: check_corpus(json_mode=json_mode)),
        ("db",       lambda: check_db(json_mode=json_mode)),
        ("safety",   lambda: check_safety(json_mode=json_mode)),
        ("ollama",   lambda: check_ollama(json_mode=json_mode)),
        ("network",  lambda: check_network(json_mode=json_mode)),
    ]
    # Hard-required steps; if these emit error, init fails.
    hard = {"python", "pip", "py_deps", "db", "safety"}
    for name, fn in steps:
        try:
            ok = fn()
        except Exception as e:
            emit(name, "error", f"unhandled: {e}", json_mode=json_mode)
            ok = False
        if not ok and name in hard:
            had_error = True

    emit("done",
         "error" if had_error else "ok",
         "init finished with errors" if had_error else "init complete",
         json_mode=json_mode)
    return 1 if had_error else 0


if __name__ == "__main__":
    sys.exit(main())

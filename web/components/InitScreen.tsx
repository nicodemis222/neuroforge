import { useEffect, useRef, useState } from "react";

type Status = {
  ready: boolean;
  platform: string;
  python: { version: string; ok: boolean };
  py_deps_ok: boolean;
  node_ok: boolean;
  npm_ok: boolean;
  web_deps_ok: boolean;
  db_ok: boolean;
  corpus_pdf_count: number;
  corpus_pdfs: string[];
  ollama_ok: boolean;
};

type Line = { step: string; status: string; message: string; ts?: number };

const SEV: Record<string, string> = {
  ok: "#3fa", warn: "#fc6", error: "#e33",
  installing: "#7be", log: "#7a8",
};

export default function InitScreen({ onReady }: { onReady: () => void }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [running, setRunning] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  const refresh = () => fetch("/api/init/status").then(r => r.json()).then(setStatus);
  useEffect(() => { refresh(); }, []);

  const start = () => {
    if (running) return;
    setLines([]);
    setRunning(true);
    const es = new EventSource("/api/init/run");
    esRef.current = es;
    es.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data) as Line;
        setLines(prev => [...prev, d]);
        if (d.step === "exit") {
          es.close();
          setRunning(false);
          refresh().then(() => {
            // If init reported ok, allow main app in.
            if (d.status === "ok") setTimeout(onReady, 600);
          });
        }
      } catch {}
    };
    es.onerror = () => {
      es.close();
      setRunning(false);
    };
  };

  const Row = ({ label, ok, hint }: { label: string; ok: boolean; hint?: string }) => (
    <div style={{ display: "grid", gridTemplateColumns: "16px 180px 1fr",
                  gap: 10, padding: "4px 0", alignItems: "center" }}>
      <span style={{ width: 10, height: 10, background: ok ? SEV.ok : SEV.warn,
                     display: "inline-block", borderRadius: 2 }}/>
      <span>{label}</span>
      <span style={{ color: "#7a8", fontSize: 11 }}>{hint}</span>
    </div>
  );

  return (
    <div style={{ background: "#0a0e14", color: "#cfe", minHeight: "100vh",
                  fontFamily: "ui-monospace,Menlo,monospace", padding: 28 }}>
      <h1 style={{ color: "#7fe", margin: 0, fontSize: 22 }}>
        NEUROFORGE — initialization
      </h1>
      <p style={{ color: "#7a8", maxWidth: 720 }}>
        First-run dependency check. The host platform is{" "}
        <code style={{ color: "#7be" }}>{status?.platform || "…"}</code>.
        Click <strong>Run init</strong> to install missing Python and Node
        packages, bootstrap the local database, and verify connectivity.
      </p>

      <section style={{ background: "#0d1420", border: "1px solid #1a2330",
                        padding: 16, marginTop: 14, maxWidth: 720 }}>
        <h2 style={{ color: "#7fe", fontSize: 14, marginTop: 0 }}>Current state</h2>
        {status ? (
          <>
            <Row label="Python ≥ 3.11" ok={status.python.ok}
                 hint={status.python.version}/>
            <Row label="Python deps installed" ok={status.py_deps_ok}
                 hint="fastapi, uvicorn, httpx, pypdf, feedparser"/>
            <Row label="SQLite database bootstrapped" ok={status.db_ok}/>
            <Row label="Patient corpus PDFs" ok={status.corpus_pdf_count > 0}
                 hint={status.corpus_pdf_count > 0
                   ? `${status.corpus_pdf_count} file(s): ${status.corpus_pdfs.join(", ")}`
                   : "Drop reports into data/patient_corpus/"}/>
            <Row label="Node.js ≥ 18 (for UI)" ok={status.node_ok}
                 hint={!status.node_ok ? "Install from nodejs.org" : "ok"}/>
            <Row label="npm" ok={status.npm_ok}/>
            <Row label="Web dependencies (node_modules)" ok={status.web_deps_ok}/>
            <Row label="Ollama (optional, PDF extraction)" ok={status.ollama_ok}
                 hint={!status.ollama_ok ? "Install from ollama.com — optional" : "running"}/>
          </>
        ) : <span style={{ color: "#7a8" }}>loading…</span>}
      </section>

      <div style={{ marginTop: 16, display: "flex", gap: 10 }}>
        <button onClick={start} disabled={running}
          style={{ background: running ? "#1a2330" : "#142030",
                   border: "1px solid #2a3a50", color: running ? "#7a8" : "#7fe",
                   padding: "8px 18px", cursor: running ? "wait" : "pointer",
                   fontFamily: "inherit", fontSize: 13 }}>
          {running ? "running…" : "Run init"}
        </button>
        <button onClick={refresh}
          style={{ background: "#0d1420", border: "1px solid #1a2330",
                   color: "#7a8", padding: "8px 14px", cursor: "pointer",
                   fontFamily: "inherit", fontSize: 13 }}>
          ↻ refresh status
        </button>
        {status?.ready && (
          <button onClick={onReady}
            style={{ background: "#142030", border: "1px solid #3fa",
                     color: "#3fa", padding: "8px 18px", cursor: "pointer",
                     fontFamily: "inherit", fontSize: 13, marginLeft: "auto" }}>
            enter dashboard →
          </button>
        )}
      </div>

      <section style={{ background: "#0d1420", border: "1px solid #1a2330",
                        marginTop: 16, padding: 14, maxWidth: 720,
                        maxHeight: 360, overflow: "auto", fontSize: 12 }}>
        <h2 style={{ color: "#7fe", fontSize: 14, marginTop: 0 }}>Init log</h2>
        {lines.length === 0 && (
          <span style={{ color: "#7a8" }}>
            no output yet — click "Run init" to begin
          </span>
        )}
        {lines.map((l, i) => (
          <div key={i} style={{ padding: "2px 0",
                                color: SEV[l.status] || "#cfe" }}>
            <span style={{ color: "#7a8" }}>[{l.step}]</span>{" "}
            <span style={{ color: SEV[l.status] || "#cfe" }}>{l.status}</span>
            {"  "}{l.message}
          </div>
        ))}
      </section>

      <p style={{ color: "#5a6", fontSize: 11, marginTop: 18, maxWidth: 720 }}>
        Windows note: if Python or Node aren't installed, the init script
        will tell you which one is missing and where to download it.
        After installing, return here and click "Run init" again.
      </p>
    </div>
  );
}

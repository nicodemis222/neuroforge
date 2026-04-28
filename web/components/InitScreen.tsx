import { useEffect, useRef, useState } from "react";
import { color, space, radius } from "../styles/tokens";

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
  ok: color.ok, warn: color.caution, error: color.block,
  installing: color.t2, log: color.textDim,
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
    <div style={{
      display: "grid", gridTemplateColumns: "16px 200px 1fr",
      gap: space.md, padding: "5px 0", alignItems: "center", fontSize: 12,
    }}>
      <span style={{
        width: 10, height: 10, background: ok ? SEV.ok : SEV.warn,
        display: "inline-block", borderRadius: 2,
      }} />
      <span>{label}</span>
      <span style={{ color: color.textFaint, fontSize: 11 }}>{hint}</span>
    </div>
  );

  return (
    <div style={{
      background: color.bg0, color: color.text, minHeight: "100vh",
      padding: space.xxl,
    }}>
      <h1 style={{ color: color.accent, margin: 0, fontSize: 22, letterSpacing: "0.05em" }}>
        NEUROFORGE — initialization
      </h1>
      <p style={{ color: color.textDim, maxWidth: 720, fontSize: 13 }}>
        First-run dependency check. Host platform:{" "}
        <code style={{ color: color.t2, background: color.bg2, padding: "1px 5px", borderRadius: 3 }}>
          {status?.platform || "…"}
        </code>.
        Click <strong>Run init</strong> to install missing Python and Node packages,
        bootstrap the local database, and verify connectivity.
      </p>

      <section style={{
        background: color.bg1, border: `1px solid ${color.border}`,
        padding: space.lg, marginTop: space.md, maxWidth: 720,
        borderRadius: radius.md,
      }}>
        <h2 style={{ color: color.accent, fontSize: 13, marginTop: 0, fontWeight: 600 }}>
          CURRENT STATE
        </h2>
        {status ? (
          <>
            <Row label="Python ≥ 3.11" ok={status.python.ok} hint={status.python.version} />
            <Row label="Python deps installed" ok={status.py_deps_ok}
                 hint="fastapi, uvicorn, httpx, pypdf, feedparser" />
            <Row label="SQLite database bootstrapped" ok={status.db_ok} />
            <Row label="Patient corpus" ok={status.corpus_pdf_count > 0}
                 hint={status.corpus_pdf_count > 0
                   ? `${status.corpus_pdf_count} document(s)`
                   : "drop documents into data/patient_corpus/ (any format)"} />
            <Row label="Node.js ≥ 18 (for UI)" ok={status.node_ok}
                 hint={!status.node_ok ? "install from nodejs.org" : ""} />
            <Row label="npm" ok={status.npm_ok} />
            <Row label="Web dependencies (node_modules)" ok={status.web_deps_ok} />
            <Row label="Ollama (optional, document extraction)" ok={status.ollama_ok}
                 hint={!status.ollama_ok ? "install from ollama.com — optional" : "running"} />
          </>
        ) : <span style={{ color: color.textFaint }}>loading…</span>}
      </section>

      <div style={{ marginTop: space.lg, display: "flex", gap: space.sm }}>
        <button onClick={start} disabled={running}
          style={{
            background: running ? color.bg2 : color.bg3,
            border: `1px solid ${color.borderStrong}`,
            color: running ? color.textFaint : color.accent,
            padding: `${space.sm}px ${space.xl}px`,
            cursor: running ? "wait" : "pointer",
            fontFamily: "inherit", fontSize: 13,
            borderRadius: radius.sm, fontWeight: 600,
          }}>
          {running ? "running…" : "Run init"}
        </button>
        <button onClick={refresh}
          style={{
            background: color.bg1, border: `1px solid ${color.border}`,
            color: color.textDim, padding: `${space.sm}px ${space.lg}px`,
            cursor: "pointer", fontFamily: "inherit", fontSize: 13,
            borderRadius: radius.sm,
          }}>
          ↻ refresh status
        </button>
        {status?.ready && (
          <button onClick={onReady}
            style={{
              background: color.bg3, border: `1px solid ${color.ok}`,
              color: color.ok, padding: `${space.sm}px ${space.xl}px`,
              cursor: "pointer", fontFamily: "inherit", fontSize: 13,
              marginLeft: "auto", borderRadius: radius.sm, fontWeight: 600,
            }}>
            enter dashboard →
          </button>
        )}
      </div>

      <section style={{
        background: color.bg1, border: `1px solid ${color.border}`,
        marginTop: space.lg, padding: space.md, maxWidth: 720,
        maxHeight: 360, overflow: "auto", fontSize: 12,
        borderRadius: radius.md,
      }}>
        <h2 style={{ color: color.accent, fontSize: 13, marginTop: 0, fontWeight: 600 }}>
          INIT LOG
        </h2>
        {lines.length === 0 && (
          <span style={{ color: color.textFaint }}>
            no output yet — click "Run init" to begin
          </span>
        )}
        {lines.map((l, i) => (
          <div key={i} style={{ padding: "2px 0" }}>
            <span style={{ color: color.textFaint }}>[{l.step}]</span>{" "}
            <span style={{ color: SEV[l.status] || color.text }}>{l.status}</span>
            {"  "}<span style={{ color: color.text }}>{l.message}</span>
          </div>
        ))}
      </section>

      <p style={{ color: color.textFaint, fontSize: 11, marginTop: space.lg, maxWidth: 720 }}>
        Windows note: if Python or Node aren't installed, the init script will
        tell you which one is missing and where to download it. After installing,
        return here and click "Run init" again.
      </p>
    </div>
  );
}

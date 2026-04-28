import React, { useCallback, useEffect, useState } from "react";
import { color, space, radius } from "../styles/tokens";
import { PanelHeader } from "./PanelHeader";
import { api, type CorpusListing } from "../lib/api";

const formatBytes = (n: number): string => {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
};

export const CorpusPanel: React.FC = () => {
  const [listing, setListing] = useState<CorpusListing | null>(null);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [extractMessage, setExtractMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => api.corpusList().then(setListing), []);
  useEffect(() => { refresh(); }, [refresh]);

  const upload = async (files: FileList | File[]) => {
    setError(null);
    const arr = Array.from(files);
    if (arr.length === 0) return;
    setBusy(true);
    try {
      const res = await api.corpusUpload(arr);
      if (res.rejected?.length) {
        setError(`${res.rejected.length} file(s) rejected: ${res.rejected.map((r: any) => `${r.name} (${r.reason})`).join(", ")}`);
      }
      await refresh();
    } catch (e: any) {
      setError(`upload failed: ${e?.message || e}`);
    }
    setBusy(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDrag(false);
    upload(e.dataTransfer.files);
  };

  const remove = async (name: string) => {
    if (!confirm(`Delete ${name}? This removes the file from data/patient_corpus/.`)) return;
    await api.corpusDelete(name);
    await refresh();
  };

  const extract = async () => {
    setExtractMessage("extraction queued — running in background");
    try {
      await api.corpusExtract();
      setTimeout(() => setExtractMessage(null), 6000);
    } catch (e: any) {
      setExtractMessage(`extract failed: ${e?.message || e}`);
    }
  };

  return (
    <div style={{ display: "grid", gridTemplateRows: "auto 1fr", height: "100%", overflow: "hidden" }}>
      <PanelHeader
        title="Document corpus"
        subtitle="ingest clinical reports — everything stays local · 16 file formats supported"
      />
      <div style={{ padding: space.xl, overflow: "auto" }}>
      <div style={{ maxWidth: 880, margin: "0 auto" }}>
        <p style={{ color: color.textDim, fontSize: 12, marginTop: 0, marginBottom: space.lg }}>
          Drop clinical documents into the zone below. Files live under
          <code style={{ background: color.bg2, padding: "1px 5px", borderRadius: 3, margin: "0 4px" }}>data/patient_corpus/</code>
          and are gitignored. Extraction populates
          <code style={{ background: color.bg2, padding: "1px 5px", borderRadius: 3, margin: "0 4px" }}>profile.json</code>
          which drives the hypothesis, safety screen, and briefing anchors —
          replacing the synthetic example.
        </p>

        <div
          onDragOver={e => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          style={{
            border: `2px dashed ${drag ? color.accent : color.border}`,
            background: drag ? color.accentBg : color.bg1,
            borderRadius: radius.md, padding: space.xxl,
            textAlign: "center", transition: "all 0.12s",
            marginBottom: space.lg,
          }}
        >
          <div style={{ fontSize: 13, color: color.text, marginBottom: space.sm }}>
            {drag ? "release to upload" : "drag documents here"}
          </div>
          <div style={{ fontSize: 11, color: color.textDim, marginBottom: space.md }}>
            or pick from disk
          </div>
          <label style={{
            display: "inline-block",
            background: color.bg3, color: color.accent,
            border: `1px solid ${color.borderStrong}`,
            padding: `${space.sm}px ${space.lg}px`, borderRadius: radius.sm,
            cursor: "pointer", fontSize: 12,
          }}>
            choose files
            <input type="file" multiple style={{ display: "none" }}
                   onChange={e => e.target.files && upload(e.target.files)} />
          </label>
          <div style={{ marginTop: space.md, fontSize: 10, color: color.textFaint }}>
            supported: {listing?.supported_extensions.join("  ·  ")}
          </div>
        </div>

        {error && (
          <div style={{
            background: "rgba(232,90,90,0.1)", border: `1px solid ${color.block}`,
            color: color.block, padding: space.md, borderRadius: radius.sm,
            fontSize: 12, marginBottom: space.md,
          }}>{error}</div>
        )}

        <div style={{
          background: color.bg1, border: `1px solid ${color.border}`,
          borderRadius: radius.md, marginBottom: space.lg,
        }}>
          <div style={{
            padding: space.md, borderBottom: `1px solid ${color.border}`,
            display: "flex", justifyContent: "space-between", alignItems: "center",
          }}>
            <span style={{ fontSize: 12, fontWeight: 500 }}>
              files · {listing?.files.length || 0}
            </span>
            <button
              onClick={extract}
              disabled={!listing?.files.length || busy}
              style={{
                background: listing?.files.length ? color.accent : color.bg2,
                color: listing?.files.length ? color.bg0 : color.textFaint,
                border: "none", padding: `${space.xs}px ${space.md}px`,
                borderRadius: radius.sm, fontSize: 11, fontWeight: 600,
                cursor: listing?.files.length ? "pointer" : "not-allowed",
              }}
            >
              ▶ extract → profile
            </button>
          </div>
          {listing?.files.length === 0 && (
            <div style={{ padding: space.lg, color: color.textFaint, fontSize: 12, textAlign: "center" }}>
              no files yet
            </div>
          )}
          {listing?.files.map(f => (
            <div key={f.name} style={{
              padding: `${space.sm}px ${space.md}px`,
              borderTop: `1px solid ${color.border}`,
              display: "grid", gridTemplateColumns: "1fr auto auto auto",
              gap: space.md, alignItems: "center", fontSize: 12,
            }}>
              <span style={{ color: f.supported ? color.text : color.warn, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {f.name}
              </span>
              <span style={{ color: color.textFaint, fontSize: 10 }}>{f.ext}</span>
              <span style={{ color: color.textFaint, fontSize: 10 }}>{formatBytes(f.size_bytes)}</span>
              <button onClick={() => remove(f.name)} style={{
                background: "transparent", border: `1px solid ${color.border}`,
                color: color.textDim, padding: "2px 8px", borderRadius: radius.sm,
                cursor: "pointer", fontSize: 10,
              }}>delete</button>
            </div>
          ))}
        </div>

        {extractMessage && (
          <div style={{
            background: color.accentBg, border: `1px solid ${color.accent}`,
            color: color.accent, padding: space.md, borderRadius: radius.sm,
            fontSize: 12, marginBottom: space.md,
          }}>{extractMessage}</div>
        )}

        <div style={{ color: color.textFaint, fontSize: 11, lineHeight: 1.6 }}>
          <strong style={{ color: color.text }}>Note:</strong> extraction uses Ollama
          (default model <code>qwen2.5:7b</code>). If Ollama is not running, the platform
          will keep the synthetic example profile. Install from{" "}
          <a href="https://ollama.com">ollama.com</a> and run{" "}
          <code>ollama pull qwen2.5:7b</code>.
        </div>
      </div>
      </div>
    </div>
  );
};

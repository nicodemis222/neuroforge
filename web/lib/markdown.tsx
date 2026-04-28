/**
 * Lightweight markdown renderer — handles headings, paragraphs, lists, links,
 * inline code, bold/italic, and horizontal rules. Enough for our briefings;
 * avoids pulling react-markdown as a dependency.
 */

import React from "react";

type Block =
  | { type: "h"; level: 1 | 2 | 3; text: string }
  | { type: "p"; text: string }
  | { type: "ul"; items: string[] }
  | { type: "hr" }
  | { type: "blockquote"; text: string };

const inline = (text: string): React.ReactNode[] => {
  const out: React.ReactNode[] = [];
  // Match: code, bold, italic, links — simplest precedence first.
  const re =
    /(\[([^\]]+)\]\(([^)]+)\))|(`([^`]+)`)|(\*\*([^*]+)\*\*)|(\*([^*]+)\*)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    if (m[1]) {
      out.push(
        <a key={i++} href={m[3]} target="_blank" rel="noreferrer">{m[2]}</a>
      );
    } else if (m[4]) {
      out.push(<code key={i++}>{m[5]}</code>);
    } else if (m[6]) {
      out.push(<strong key={i++}>{m[7]}</strong>);
    } else if (m[8]) {
      out.push(<em key={i++}>{m[9]}</em>);
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
};

const parse = (src: string): Block[] => {
  const lines = src.split("\n");
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }

    if (/^---+\s*$/.test(line)) { blocks.push({ type: "hr" }); i++; continue; }

    const h = /^(#{1,3})\s+(.+)$/.exec(line);
    if (h) {
      blocks.push({ type: "h", level: h[1].length as 1 | 2 | 3, text: h[2] });
      i++; continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ""));
        i++;
      }
      blocks.push({ type: "ul", items });
      continue;
    }

    if (line.startsWith("> ")) {
      blocks.push({ type: "blockquote", text: line.slice(2) });
      i++; continue;
    }

    const buf: string[] = [line];
    i++;
    while (i < lines.length && lines[i].trim() &&
           !/^(#{1,3})\s+/.test(lines[i]) &&
           !/^\s*[-*]\s+/.test(lines[i]) &&
           !/^---+\s*$/.test(lines[i])) {
      buf.push(lines[i]); i++;
    }
    blocks.push({ type: "p", text: buf.join(" ") });
  }
  return blocks;
};

export const Markdown: React.FC<{ src: string }> = ({ src }) => {
  const blocks = parse(src);
  return (
    <div className="md">
      {blocks.map((b, i) => {
        if (b.type === "h") {
          if (b.level === 1) return <h1 key={i}>{inline(b.text)}</h1>;
          if (b.level === 2) return <h2 key={i}>{inline(b.text)}</h2>;
          return <h3 key={i}>{inline(b.text)}</h3>;
        }
        if (b.type === "p") return <p key={i}>{inline(b.text)}</p>;
        if (b.type === "ul")
          return <ul key={i}>{b.items.map((it, j) => <li key={j}>{inline(it)}</li>)}</ul>;
        if (b.type === "hr") return <hr key={i} />;
        if (b.type === "blockquote") return <blockquote key={i}>{inline(b.text)}</blockquote>;
        return null;
      })}
    </div>
  );
};

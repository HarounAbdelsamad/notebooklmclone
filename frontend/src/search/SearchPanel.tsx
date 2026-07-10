import { Fragment, useState } from "react";
import { useSearch } from "../api/hooks";

const HIGHLIGHT_START = "<mark>";
const HIGHLIGHT_END = "</mark>";

/**
 * Renders a ts_headline-style snippet safely. The backend wraps matched
 * terms in `<mark>...</mark>` but does NOT escape the surrounding source
 * text (which is attacker-controlled document/note/chat content). We must
 * never inject that text as raw HTML. Instead, split on the highlight
 * delimiters and render plain text segments as React text nodes (which are
 * auto-escaped) and highlighted segments as real `<mark>` elements.
 */
function HighlightedSnippet({ snippet }: { snippet: string }) {
  const parts: Array<{ text: string; highlighted: boolean }> = [];
  let cursor = 0;

  while (cursor < snippet.length) {
    const startIdx = snippet.indexOf(HIGHLIGHT_START, cursor);
    if (startIdx === -1) {
      parts.push({ text: snippet.slice(cursor), highlighted: false });
      break;
    }
    if (startIdx > cursor) {
      parts.push({ text: snippet.slice(cursor, startIdx), highlighted: false });
    }
    const contentStart = startIdx + HIGHLIGHT_START.length;
    const endIdx = snippet.indexOf(HIGHLIGHT_END, contentStart);
    if (endIdx === -1) {
      // Unterminated marker — treat the rest as plain text, do not risk
      // interpreting it as markup.
      parts.push({ text: snippet.slice(startIdx), highlighted: false });
      break;
    }
    parts.push({ text: snippet.slice(contentStart, endIdx), highlighted: true });
    cursor = endIdx + HIGHLIGHT_END.length;
  }

  return (
    <>
      {parts.map((part, i) =>
        part.highlighted ? <mark key={i}>{part.text}</mark> : <Fragment key={i}>{part.text}</Fragment>
      )}
    </>
  );
}

export function SearchPanel({ notebookId }: { notebookId: string }) {
  const [term, setTerm] = useState("");
  const [query, setQuery] = useState("");
  const { data, isFetching } = useSearch(notebookId, query);

  return (
    <div>
      <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
        <input
          placeholder="Search sources, notes, chats…"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && setQuery(term)}
        />
        <button onClick={() => setQuery(term)}>Go</button>
      </div>
      {isFetching && <p className="muted">Searching…</p>}
      {data?.hits.map((hit) => (
        <div key={`${hit.scope}-${hit.id}`} className="card" style={{ marginBottom: 8 }}>
          <span className="badge">{hit.scope}</span>{" "}
          <strong style={{ fontSize: 13 }}>{hit.title ?? "Untitled"}</strong>
          <p className="muted" style={{ margin: "6px 0 0", fontSize: 13 }}>
            <HighlightedSnippet snippet={hit.snippet} />
          </p>
        </div>
      ))}
      {data && data.hits.length === 0 && <p className="muted">No results.</p>}
    </div>
  );
}

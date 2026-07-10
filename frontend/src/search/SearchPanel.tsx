import { useState } from "react";
import { useSearch } from "../api/hooks";

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
          <p
            className="muted"
            style={{ margin: "6px 0 0", fontSize: 13 }}
            dangerouslySetInnerHTML={{ __html: hit.snippet }}
          />
        </div>
      ))}
      {data && data.hits.length === 0 && <p className="muted">No results.</p>}
    </div>
  );
}

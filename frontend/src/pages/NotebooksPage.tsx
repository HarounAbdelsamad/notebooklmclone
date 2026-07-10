import { useState } from "react";
import { Link } from "react-router-dom";
import { useCreateNotebook, useNotebooks } from "../api/hooks";

export function NotebooksPage() {
  const { data: notebooks, isLoading } = useNotebooks();
  const createNotebook = useCreateNotebook();
  const [title, setTitle] = useState("");

  const handleCreate = () => {
    const t = title.trim() || "Untitled notebook";
    createNotebook.mutate({ title: t }, { onSuccess: () => setTitle("") });
  };

  return (
    <div className="container">
      <div className="card" style={{ marginBottom: 20 }}>
        <h2 style={{ marginTop: 0 }}>New notebook</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            placeholder="Notebook title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <button className="primary" onClick={handleCreate} disabled={createNotebook.isPending}>
            Create
          </button>
        </div>
      </div>

      <h2>Your notebooks</h2>
      {isLoading && <p className="muted">Loading…</p>}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))" }}>
        {notebooks?.map((nb) => (
          <Link key={nb.id} to={`/notebooks/${nb.id}`} className="card">
            <strong>{nb.title}</strong>
            <p className="muted" style={{ margin: "8px 0 0", fontSize: 13 }}>
              {nb.description || "No description"}
            </p>
          </Link>
        ))}
        {notebooks?.length === 0 && <p className="muted">No notebooks yet — create one above.</p>}
      </div>
    </div>
  );
}

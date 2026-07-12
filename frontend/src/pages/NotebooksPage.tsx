import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useCreateNotebook, useDeleteNotebook, useNotebooks } from "../api/hooks";
import { MoreVerticalIcon, TrashIcon } from "../components/icons";
import { Modal } from "../components/Modal";
import type { Notebook } from "../api/types";

function formatCreatedAt(createdAt: string): string | null {
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return null;
  return `Created ${date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })}`;
}

function NotebookCard({ notebook }: { notebook: Notebook }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const deleteNotebook = useDeleteNotebook();
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  const openConfirm = () => {
    setMenuOpen(false);
    setConfirmOpen(true);
  };

  const confirmDelete = () => {
    deleteNotebook.mutate(notebook.id, {
      onSuccess: () => setConfirmOpen(false),
    });
  };

  const created = formatCreatedAt(notebook.created_at);

  return (
    <div className="notebook-card-wrap">
      <Link to={`/notebooks/${notebook.id}`} className="card notebook-card">
        <strong>{notebook.title}</strong>
        <p className="muted" style={{ margin: "8px 0 0", fontSize: 13 }}>
          {notebook.description || "No description"}
        </p>
        {created && (
          <p className="muted" style={{ margin: "6px 0 0", fontSize: 12 }}>
            {created}
          </p>
        )}
      </Link>

      <div className="notebook-card-menu" ref={menuRef}>
        <button
          type="button"
          className="ghost notebook-card-menu-btn"
          title="Notebook options"
          aria-label="Notebook options"
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setMenuOpen((open) => !open);
          }}
        >
          <MoreVerticalIcon />
        </button>
        {menuOpen && (
          <div
            className="dropdown-menu"
            role="menu"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              role="menuitem"
              className="dropdown-menu-item danger"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                openConfirm();
              }}
            >
              <TrashIcon />
              Delete notebook
            </button>
          </div>
        )}
      </div>

      {confirmOpen && (
        <Modal title="Delete notebook?" onClose={() => setConfirmOpen(false)}>
          <p style={{ marginTop: 0 }}>
            Permanently delete <strong>{notebook.title}</strong>? This will also delete all of its
            documents, notes, chats, and generated outputs. This cannot be undone.
          </p>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
            <button
              type="button"
              className="secondary"
              onClick={() => setConfirmOpen(false)}
              disabled={deleteNotebook.isPending}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={confirmDelete}
              disabled={deleteNotebook.isPending}
              style={{ background: "var(--danger)", borderColor: "var(--danger)", color: "#fff" }}
            >
              {deleteNotebook.isPending ? "Deleting…" : "Delete"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

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
          <NotebookCard key={nb.id} notebook={nb} />
        ))}
        {notebooks?.length === 0 && <p className="muted">No notebooks yet — create one above.</p>}
      </div>
    </div>
  );
}

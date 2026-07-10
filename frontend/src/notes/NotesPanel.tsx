import { useState } from "react";
import {
  useCreateNote,
  useDeleteNote,
  useNotes,
  useUpdateNote,
} from "../api/hooks";
import type { Note } from "../api/types";

function NoteEditor({ note, notebookId }: { note: Note; notebookId: string }) {
  const update = useUpdateNote(notebookId);
  const del = useDeleteNote(notebookId);
  const [content, setContent] = useState(note.content);
  const [title, setTitle] = useState(note.title);
  const dirty = content !== note.content || title !== note.title;

  return (
    <div className="card" style={{ marginBottom: 10 }}>
      <input value={title} onChange={(e) => setTitle(e.target.value)} style={{ marginBottom: 6 }} />
      <textarea rows={4} value={content} onChange={(e) => setContent(e.target.value)} />
      <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
        <button
          className="primary"
          disabled={!dirty || update.isPending}
          onClick={() => update.mutate({ id: note.id, title, content })}
        >
          Save
        </button>
        <button onClick={() => del.mutate(note.id)}>Delete</button>
      </div>
    </div>
  );
}

export function NotesPanel({ notebookId }: { notebookId: string }) {
  const { data: notes } = useNotes(notebookId);
  const create = useCreateNote(notebookId);

  return (
    <div>
      <button
        className="primary"
        style={{ width: "100%", marginBottom: 12 }}
        onClick={() => create.mutate({ title: "Untitled note", content: "" })}
      >
        + New note
      </button>
      {notes?.map((n) => (
        <NoteEditor key={n.id} note={n} notebookId={notebookId} />
      ))}
      {notes?.length === 0 && <p className="muted">No notes yet.</p>}
    </div>
  );
}

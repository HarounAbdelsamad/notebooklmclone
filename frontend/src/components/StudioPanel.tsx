import { useState } from "react";
import { NotesPanel } from "../notes/NotesPanel";
import { OutputsPanel } from "../outputs/OutputsPanel";
import { SearchPanel } from "../search/SearchPanel";

type Tab = "notes" | "outputs" | "search";

export function StudioPanel({ notebookId }: { notebookId: string }) {
  const [tab, setTab] = useState<Tab>("outputs");

  return (
    <div className="panel">
      <h2>Studio</h2>
      <div className="tabs">
        <button className={tab === "outputs" ? "active" : ""} onClick={() => setTab("outputs")}>
          Outputs
        </button>
        <button className={tab === "notes" ? "active" : ""} onClick={() => setTab("notes")}>
          Notes
        </button>
        <button className={tab === "search" ? "active" : ""} onClick={() => setTab("search")}>
          Search
        </button>
      </div>
      {tab === "outputs" && <OutputsPanel notebookId={notebookId} />}
      {tab === "notes" && <NotesPanel notebookId={notebookId} />}
      {tab === "search" && <SearchPanel notebookId={notebookId} />}
    </div>
  );
}

import { useRef, useState } from "react";
import {
  useDeleteDocument,
  useDocuments,
  useIngestUrl,
  useUploadDocument,
} from "../api/hooks";
import type { DocumentStatus, SourceType } from "../api/types";

const EXT_TO_TYPE: Record<string, SourceType> = {
  pdf: "pdf",
  docx: "docx",
  doc: "docx",
  txt: "txt",
  md: "markdown",
  markdown: "markdown",
  html: "html",
  htm: "html",
  pptx: "ppt",
  ppt: "ppt",
  csv: "csv",
};

function inferType(filename: string): SourceType {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  return EXT_TO_TYPE[ext] ?? "txt";
}

function statusClass(status: DocumentStatus): string {
  if (status === "ready") return "badge ready";
  if (status === "failed") return "badge failed";
  return "badge";
}

export function DocumentsPanel({ notebookId }: { notebookId: string }) {
  // Poll while anything is still processing.
  const { data: docs } = useDocuments(notebookId, true);
  const upload = useUploadDocument(notebookId);
  const ingestUrl = useIngestUrl(notebookId);
  const del = useDeleteDocument(notebookId);
  const fileRef = useRef<HTMLInputElement>(null);
  const [url, setUrl] = useState("");

  const onFiles = (files: FileList | null) => {
    if (!files) return;
    for (const file of Array.from(files)) {
      upload.mutate({ file, sourceType: inferType(file.name) });
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div className="panel">
      <h2>Sources</h2>

      <input
        ref={fileRef}
        type="file"
        multiple
        style={{ display: "none" }}
        onChange={(e) => onFiles(e.target.files)}
        accept=".pdf,.docx,.txt,.md,.markdown,.html,.htm,.pptx,.ppt,.csv"
      />
      <button className="primary" style={{ width: "100%" }} onClick={() => fileRef.current?.click()}>
        + Upload files
      </button>

      <div style={{ display: "flex", gap: 6, margin: "10px 0 16px" }}>
        <input
          placeholder="Add a URL…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <button
          onClick={() => {
            if (url.trim()) ingestUrl.mutate({ url: url.trim() }, { onSuccess: () => setUrl("") });
          }}
        >
          Add
        </button>
      </div>

      {docs?.map((doc) => (
        <div key={doc.id} className="list-row">
          <div style={{ overflow: "hidden" }}>
            <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {doc.filename}
            </div>
            <span className={statusClass(doc.status)}>{doc.status}</span>{" "}
            <span className="muted" style={{ fontSize: 12 }}>
              {doc.source_type}
            </span>
          </div>
          <button
            title="Delete"
            onClick={() => del.mutate(doc.id)}
            style={{ padding: "4px 8px" }}
          >
            ✕
          </button>
        </div>
      ))}
      {docs?.length === 0 && <p className="muted">No sources yet.</p>}
    </div>
  );
}

import { useState } from "react";
import { useGenerateOutput, useOutputs } from "../api/hooks";
import type { OutputType } from "../api/types";

const TYPES: { type: OutputType; label: string }[] = [
  { type: "summary", label: "Summary" },
  { type: "faq", label: "FAQ" },
  { type: "study_guide", label: "Study guide" },
  { type: "briefing", label: "Briefing" },
  { type: "timeline", label: "Timeline" },
];

export function OutputsPanel({ notebookId }: { notebookId: string }) {
  const { data: outputs } = useOutputs(notebookId);
  const generate = useGenerateOutput(notebookId);
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
        {TYPES.map((t) => (
          <button key={t.type} onClick={() => generate.mutate(t.type)}>
            {t.label}
          </button>
        ))}
      </div>
      {outputs?.map((o) => (
        <div key={o.id} className="card" style={{ marginBottom: 10 }}>
          <div
            style={{ display: "flex", justifyContent: "space-between", cursor: "pointer" }}
            onClick={() => setOpenId(openId === o.id ? null : o.id)}
          >
            <strong>{o.title}</strong>
            <span className="muted">{o.content ? "▾" : "generating…"}</span>
          </div>
          {openId === o.id && o.content && (
            <p style={{ whiteSpace: "pre-wrap", marginBottom: 0, fontSize: 14 }}>{o.content}</p>
          )}
        </div>
      ))}
      {outputs?.length === 0 && <p className="muted">Generate an overview from your sources.</p>}
    </div>
  );
}

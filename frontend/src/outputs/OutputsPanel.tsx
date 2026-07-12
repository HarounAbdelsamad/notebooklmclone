import { useState } from "react";
import { useGenerateOutput, useOutputs } from "../api/hooks";
import type { OutputType } from "../api/types";
import { Modal } from "../components/Modal";
import {
  BriefingIcon,
  FaqIcon,
  StudyGuideIcon,
  SummaryIcon,
  TimelineIcon,
} from "../components/icons";
import type { SVGProps } from "react";

const TYPES: { type: OutputType; label: string; Icon: (props: SVGProps<SVGSVGElement>) => JSX.Element }[] = [
  { type: "summary", label: "Summary", Icon: SummaryIcon },
  { type: "faq", label: "FAQ", Icon: FaqIcon },
  { type: "study_guide", label: "Study guide", Icon: StudyGuideIcon },
  { type: "briefing", label: "Briefing", Icon: BriefingIcon },
  { type: "timeline", label: "Timeline", Icon: TimelineIcon },
];

export function OutputsPanel({ notebookId }: { notebookId: string }) {
  const { data: outputs } = useOutputs(notebookId);
  const generate = useGenerateOutput(notebookId);
  const [openId, setOpenId] = useState<string | null>(null);

  const openOutput = outputs?.find((o) => o.id === openId);

  return (
    <div>
      <div className="studio-actions">
        {TYPES.map(({ type, label, Icon }) => (
          <button
            key={type}
            className="secondary studio-action-btn"
            onClick={() => generate.mutate(type)}
            disabled={generate.isPending}
          >
            <Icon />
            <span>{label}</span>
          </button>
        ))}
      </div>
      {outputs?.map((o) => (
        <div key={o.id} className="card" style={{ marginBottom: 10 }}>
          <div
            style={{ display: "flex", justifyContent: "space-between", cursor: "pointer" }}
            onClick={() => o.content && setOpenId(o.id)}
          >
            <strong>{o.title}</strong>
            <span className="muted">{o.content ? "▾" : "generating…"}</span>
          </div>
        </div>
      ))}
      {outputs?.length === 0 && <p className="muted">Generate an overview from your sources.</p>}

      {openOutput && openOutput.content && (
        <Modal title={openOutput.title} onClose={() => setOpenId(null)}>
          {openOutput.content}
        </Modal>
      )}
    </div>
  );
}

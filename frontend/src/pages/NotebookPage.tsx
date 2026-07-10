import { useParams } from "react-router-dom";
import { ChatPanel } from "../chat/ChatPanel";
import { StudioPanel } from "../components/StudioPanel";
import { DocumentsPanel } from "../documents/DocumentsPanel";

export function NotebookPage() {
  const { notebookId } = useParams<{ notebookId: string }>();
  if (!notebookId) return null;

  return (
    <div className="workspace">
      <DocumentsPanel notebookId={notebookId} />
      <ChatPanel notebookId={notebookId} />
      <StudioPanel notebookId={notebookId} />
    </div>
  );
}

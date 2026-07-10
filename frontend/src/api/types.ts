export type DocumentStatus =
  | "queued"
  | "extracting"
  | "cleaning"
  | "chunking"
  | "embedding"
  | "ready"
  | "failed";

export type SourceType =
  | "pdf"
  | "docx"
  | "txt"
  | "markdown"
  | "html"
  | "url"
  | "ppt"
  | "csv";

export interface Notebook {
  id: string;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotebookDetail extends Notebook {
  document_count: number;
  note_count: number;
  chat_count: number;
}

export interface DocumentItem {
  id: string;
  notebook_id: string;
  filename: string;
  source_type: SourceType;
  mime_type: string | null;
  source_url: string | null;
  status: DocumentStatus;
  error: string | null;
  page_count: number | null;
  char_count: number | null;
  processed_at: string | null;
  created_at: string;
}

export interface Note {
  id: string;
  notebook_id: string;
  title: string;
  content: string;
  source: "user" | "generated";
  created_at: string;
  updated_at: string;
}

export interface Chat {
  id: string;
  notebook_id: string;
  title: string;
  created_at: string;
}

export interface Citation {
  chunk_id: string | null;
  document_id: string | null;
  snippet: string | null;
  page_number: number | null;
  score: number | null;
  rank: number | null;
}

export interface Message {
  id: string;
  chat_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations: Citation[];
  created_at: string;
}

export interface SearchHit {
  scope: "documents" | "notes" | "chats";
  id: string;
  title: string | null;
  snippet: string;
  score: number;
  notebook_id: string;
  document_id: string | null;
  page_number: number | null;
}

export interface SearchResponse {
  query: string;
  hits: SearchHit[];
}

export type OutputType = "summary" | "faq" | "study_guide" | "briefing" | "timeline";

export interface GeneratedOutput {
  id: string;
  notebook_id: string;
  type: OutputType;
  title: string;
  content: string;
  params: Record<string, unknown> | null;
  created_at: string;
}

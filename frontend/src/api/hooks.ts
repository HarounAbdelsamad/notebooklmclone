import { useAuth } from "@clerk/clerk-react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import { useCallback } from "react";
import { apiFetch, type TokenGetter } from "./client";
import type {
  Chat,
  DocumentItem,
  GeneratedOutput,
  Message,
  Note,
  Notebook,
  NotebookDetail,
  OutputType,
  SearchResponse,
} from "./types";

/** Bind the current Clerk session's token getter for use with apiFetch. */
export function useToken(): TokenGetter {
  const { getToken } = useAuth();
  return useCallback(() => getToken(), [getToken]);
}

// -------------------------------------------------------------------- notebooks

export function useNotebooks() {
  const getToken = useToken();
  return useQuery({
    queryKey: ["notebooks"],
    queryFn: () => apiFetch<Notebook[]>(getToken, "/notebooks"),
  });
}

export function useNotebook(id: string) {
  const getToken = useToken();
  return useQuery({
    queryKey: ["notebook", id],
    queryFn: () => apiFetch<NotebookDetail>(getToken, `/notebooks/${id}`),
  });
}

export function useCreateNotebook() {
  const getToken = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { title: string; description?: string }) =>
      apiFetch<Notebook>(getToken, "/notebooks", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidate(qc, ["notebooks"]),
  });
}

// -------------------------------------------------------------------- documents

export function useDocuments(notebookId: string, poll = false) {
  const getToken = useToken();
  return useQuery({
    queryKey: ["documents", notebookId],
    queryFn: () =>
      apiFetch<DocumentItem[]>(getToken, `/notebooks/${notebookId}/documents`),
    // Poll while any document is still processing.
    refetchInterval: poll ? 2500 : false,
  });
}

export function useUploadDocument(notebookId: string) {
  const getToken = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { file: File; sourceType: string }) => {
      const form = new FormData();
      form.append("file", args.file);
      form.append("source_type", args.sourceType);
      return apiFetch<DocumentItem>(getToken, `/notebooks/${notebookId}/documents`, {
        method: "POST",
        body: form,
      });
    },
    onSuccess: () => invalidate(qc, ["documents", notebookId]),
  });
}

export function useIngestUrl(notebookId: string) {
  const getToken = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { url: string; title?: string }) =>
      apiFetch<DocumentItem>(getToken, `/notebooks/${notebookId}/documents/url`, {
        method: "POST",
        body: JSON.stringify({ ...body, source_type: "url" }),
      }),
    onSuccess: () => invalidate(qc, ["documents", notebookId]),
  });
}

export function useDeleteDocument(notebookId: string) {
  const getToken = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) =>
      apiFetch<void>(getToken, `/notebooks/${notebookId}/documents/${documentId}`, {
        method: "DELETE",
      }),
    onSuccess: () => invalidate(qc, ["documents", notebookId]),
  });
}

// -------------------------------------------------------------------- notes

export function useNotes(notebookId: string) {
  const getToken = useToken();
  return useQuery({
    queryKey: ["notes", notebookId],
    queryFn: () => apiFetch<Note[]>(getToken, `/notebooks/${notebookId}/notes`),
  });
}

export function useCreateNote(notebookId: string) {
  const getToken = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { title: string; content: string }) =>
      apiFetch<Note>(getToken, `/notebooks/${notebookId}/notes`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => invalidate(qc, ["notes", notebookId]),
  });
}

export function useUpdateNote(notebookId: string) {
  const getToken = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { id: string; title?: string; content?: string }) =>
      apiFetch<Note>(getToken, `/notebooks/${notebookId}/notes/${args.id}`, {
        method: "PATCH",
        body: JSON.stringify({ title: args.title, content: args.content }),
      }),
    onSuccess: () => invalidate(qc, ["notes", notebookId]),
  });
}

export function useDeleteNote(notebookId: string) {
  const getToken = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(getToken, `/notebooks/${notebookId}/notes/${id}`, {
        method: "DELETE",
      }),
    onSuccess: () => invalidate(qc, ["notes", notebookId]),
  });
}

// -------------------------------------------------------------------- chats

export function useChats(notebookId: string) {
  const getToken = useToken();
  return useQuery({
    queryKey: ["chats", notebookId],
    queryFn: () => apiFetch<Chat[]>(getToken, `/notebooks/${notebookId}/chats`),
  });
}

export function useChat(notebookId: string, chatId: string | null) {
  const getToken = useToken();
  return useQuery({
    queryKey: ["chat", notebookId, chatId],
    queryFn: () =>
      apiFetch<Chat & { messages: Message[] }>(
        getToken,
        `/notebooks/${notebookId}/chats/${chatId}`,
      ),
    enabled: Boolean(chatId),
  });
}

// -------------------------------------------------------------------- search

export function useSearch(notebookId: string, query: string) {
  const getToken = useToken();
  return useQuery({
    queryKey: ["search", notebookId, query],
    queryFn: () =>
      apiFetch<SearchResponse>(
        getToken,
        `/notebooks/${notebookId}/search?q=${encodeURIComponent(query)}`,
      ),
    enabled: query.trim().length > 0,
  });
}

// -------------------------------------------------------------------- outputs

export function useOutputs(notebookId: string) {
  const getToken = useToken();
  return useQuery({
    queryKey: ["outputs", notebookId],
    queryFn: () =>
      apiFetch<GeneratedOutput[]>(getToken, `/notebooks/${notebookId}/outputs`),
    refetchInterval: 4000,
  });
}

export function useGenerateOutput(notebookId: string) {
  const getToken = useToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (type: OutputType) =>
      apiFetch<GeneratedOutput>(getToken, `/notebooks/${notebookId}/outputs`, {
        method: "POST",
        body: JSON.stringify({ type }),
      }),
    onSuccess: () => invalidate(qc, ["outputs", notebookId]),
  });
}

function invalidate(qc: QueryClient, key: unknown[]) {
  return qc.invalidateQueries({ queryKey: key });
}

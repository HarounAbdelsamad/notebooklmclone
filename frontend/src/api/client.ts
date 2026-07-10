const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export type TokenGetter = () => Promise<string | null>;

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function authHeaders(getToken: TokenGetter): Promise<Record<string, string>> {
  const token = await getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiFetch<T>(
  getToken: TokenGetter,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.body && !(options.body instanceof FormData)
      ? { "Content-Type": "application/json" }
      : {}),
    ...(await authHeaders(getToken)),
    ...((options.headers as Record<string, string>) ?? {}),
  };
  const resp = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!resp.ok) {
    const text = await resp.text().catch(() => resp.statusText);
    throw new ApiError(resp.status, text || resp.statusText);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export interface SseHandlers {
  onStart?: (data: { chat_id: string }) => void;
  onToken?: (text: string) => void;
  onCitations?: (citations: unknown[]) => void;
  onDone?: (data: { chat_id: string; message_id: string }) => void;
  onError?: (message: string) => void;
}

/**
 * Stream a chat answer over SSE. Uses fetch + a ReadableStream reader (not EventSource)
 * so we can POST a JSON body and attach the Clerk bearer token.
 */
export async function streamAsk(
  getToken: TokenGetter,
  notebookId: string,
  body: { question: string; chat_id?: string | null },
  handlers: SseHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch(`${BASE_URL}/notebooks/${notebookId}/chats/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders(getToken)) },
    body: JSON.stringify(body),
    signal,
  });
  if (!resp.ok || !resp.body) {
    handlers.onError?.(`Request failed (${resp.status})`);
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // Parse the SSE wire format: events separated by a blank line, "event:" and "data:" fields.
  const dispatch = (rawEvent: string) => {
    let event = "message";
    const dataLines: string[] = [];
    for (const line of rawEvent.split("\n")) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        // Per SSE spec, strip exactly one leading space — do NOT trim, or token
        // spacing (e.g. leading-space word pieces) is destroyed.
        let value = line.slice(5);
        if (value.startsWith(" ")) value = value.slice(1);
        dataLines.push(value);
      }
    }
    const data = dataLines.join("\n");
    switch (event) {
      case "start":
        handlers.onStart?.(JSON.parse(data));
        break;
      case "token":
        handlers.onToken?.(data);
        break;
      case "citations":
        handlers.onCitations?.(JSON.parse(data));
        break;
      case "done":
        handlers.onDone?.(JSON.parse(data));
        break;
      case "error":
        handlers.onError?.(JSON.parse(data).message ?? "Unknown error");
        break;
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      if (rawEvent.trim()) dispatch(rawEvent);
    }
  }
}

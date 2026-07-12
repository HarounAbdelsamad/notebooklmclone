import { useRef, useState } from "react";
import { streamAsk } from "../api/client";
import { useToken } from "../api/hooks";
import type { Citation } from "../api/types";
import { StreamingStatus } from "./StreamingStatus";

interface UiMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

export function ChatPanel({ notebookId }: { notebookId: string }) {
  const getToken = useToken();
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const chatIdRef = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
    });
  };

  const send = async () => {
    const question = input.trim();
    if (!question || streaming) return;
    setInput("");
    setStreaming(true);
    setMessages((m) => [...m, { role: "user", content: question }, { role: "assistant", content: "" }]);
    scrollToBottom();

    const updateAssistant = (updater: (prev: UiMessage) => UiMessage) =>
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = updater(copy[copy.length - 1]);
        return copy;
      });

    try {
      await streamAsk(
        getToken,
        notebookId,
        { question, chat_id: chatIdRef.current },
        {
          onStart: (d) => (chatIdRef.current = d.chat_id),
          onToken: (t) => {
            updateAssistant((prev) => ({ ...prev, content: prev.content + t }));
            scrollToBottom();
          },
          onCitations: (c) =>
            updateAssistant((prev) => ({ ...prev, citations: c as Citation[] })),
          onError: (msg) =>
            updateAssistant((prev) => ({
              ...prev,
              content: prev.content || `⚠️ ${msg}`,
            })),
        },
      );
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="chat-column">
      <div className="messages" ref={scrollRef}>
        {messages.length === 0 && (
          <p className="muted">Ask a question about your sources to get a grounded, cited answer.</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.content ||
              (m.role === "assistant" && streaming && i === messages.length - 1 ? (
                <StreamingStatus />
              ) : (
                ""
              ))}
            {m.citations && m.citations.length > 0 && (
              <div style={{ marginTop: 8 }}>
                {m.citations.map((c, j) => (
                  <span key={j} className="citation-chip" title={c.snippet ?? ""}>
                    [{(c.rank ?? j) + 1}]
                    {c.page_number != null ? ` p.${c.page_number}` : ""}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="chat-input">
        <textarea
          rows={2}
          placeholder="Ask about your sources…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
        />
        <button className="primary" onClick={() => void send()} disabled={streaming}>
          {streaming ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}

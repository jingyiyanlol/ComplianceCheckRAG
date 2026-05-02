import type { Citation, DocumentScope, FeedbackRating } from "../types";

const BASE = "/api";

export interface StreamHandlers {
  onCitations: (citations: Citation[]) => void;
  onToken: (token: string) => void;
  onDone: () => void;
  onError: (err: Error) => void;
}

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

/**
 * Open an SSE stream to /chat and dispatch events to the provided handlers.
 * Returns an AbortController so the caller can cancel the stream.
 */
export function streamChat(
  conversationId: string,
  history: HistoryMessage[],
  message: string,
  docFilter: DocumentScope,
  handlers: StreamHandlers
): AbortController {
  const controller = new AbortController();

  (async () => {
    let response: Response;
    try {
      response = await fetch(`${BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          history,
          message,
          doc_filter: docFilter,
        }),
        signal: controller.signal,
      });
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        handlers.onError(err as Error);
      }
      return;
    }

    if (!response.ok || !response.body) {
      handlers.onError(new Error(`HTTP ${response.status}`));
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        const lines = part.split("\n");
        const eventLine = lines.find((l) => l.startsWith("event:"));
        const dataLine = lines.find((l) => l.startsWith("data:"));
        if (!dataLine) continue;

        const eventType = eventLine?.replace("event:", "").trim() ?? "message";
        const raw = dataLine.replace("data:", "").trim();

        if (eventType === "citations") {
          const citations: Citation[] = JSON.parse(raw);
          handlers.onCitations(citations);
        } else if (eventType === "done") {
          handlers.onDone();
        } else {
          const parsed: { token: string } = JSON.parse(raw);
          handlers.onToken(parsed.token);
        }
      }
    }
  })();

  return controller;
}

/** Submit thumbs up/down feedback for an assistant message. */
export async function submitFeedback(
  messageId: string,
  rating: FeedbackRating,
  comment?: string
): Promise<void> {
  await fetch(`${BASE}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message_id: messageId, rating, comment }),
  });
}

/** List all ingested document names. */
export async function listDocuments(): Promise<string[]> {
  const res = await fetch(`${BASE}/admin/documents`);
  if (!res.ok) return [];
  const data: { documents: string[] } = await res.json();
  return data.documents;
}

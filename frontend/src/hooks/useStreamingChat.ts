import { useCallback, useRef } from "react";
import { streamChat } from "../lib/api";
import type { Citation, DocumentScope, Message } from "../types";

interface UseStreamingChatOptions {
  conversationId: string;
  docFilter: DocumentScope;
  history: Message[];
  onAssistantStart: (messageId: string) => void;
  onToken: (messageId: string, token: string) => void;
  onCitations: (messageId: string, citations: Citation[]) => void;
  onDone: (messageId: string) => void;
  onError: (err: Error) => void;
}

export function useStreamingChat(opts: UseStreamingChatOptions) {
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    (userMessage: string) => {
      // Cancel any in-flight stream
      abortRef.current?.abort();

      const messageId = crypto.randomUUID();
      opts.onAssistantStart(messageId);

      const historyForApi = opts.history
        .filter((m) => !m.isStreaming)
        .map((m) => ({ role: m.role, content: m.content }));

      abortRef.current = streamChat(
        opts.conversationId,
        historyForApi,
        userMessage,
        opts.docFilter,
        {
          onCitations: (citations) => opts.onCitations(messageId, citations),
          onToken: (token) => opts.onToken(messageId, token),
          onDone: () => opts.onDone(messageId),
          onError: opts.onError,
        }
      );
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [opts.conversationId, opts.docFilter, opts.history]
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  return { send, cancel };
}

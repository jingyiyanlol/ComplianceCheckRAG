import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { CitationCard } from "./CitationCard";
import { FeedbackButtons } from "./FeedbackButtons";
import type { Message, FeedbackRating } from "../types";

interface MessageListProps {
  conversationId: string;
  messages: Message[];
  onFeedback: (messageId: string, rating: FeedbackRating) => void;
}

export function MessageList({ conversationId: _conversationId, messages, onFeedback }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Pause auto-scroll when user scrolls up
  function handleScroll() {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    setAutoScroll(atBottom);
  }

  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, autoScroll]);

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-4 py-4"
      aria-live="polite"
      aria-label="Conversation messages"
    >
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`mb-4 flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[85%] rounded-2xl px-4 py-3 ${
              msg.role === "user"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-800 shadow-sm ring-1 ring-gray-200"
            }`}
          >
            {msg.role === "assistant" ? (
              <>
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown>{msg.content || "…"}</ReactMarkdown>
                </div>
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 space-y-1">
                    {msg.citations.map((c, i) => (
                      <CitationCard key={c.chunk_id} citation={c} index={i + 1} />
                    ))}
                  </div>
                )}
                {!msg.isStreaming && (
                  <FeedbackButtons
                    messageId={msg.id}
                    currentRating={msg.feedbackRating}
                    onRated={(rating) => onFeedback(msg.id, rating)}
                  />
                )}
              </>
            ) : (
              <p className="text-sm">{msg.content}</p>
            )}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

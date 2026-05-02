import { useCallback } from "react";
import type { Conversation, DocumentScope, Message, FeedbackRating } from "../types";
import { useLocalStorage } from "./useLocalStorage";

const STORAGE_KEY = "ccrag_conversations";
const ACTIVE_KEY = "ccrag_active_conversation";

function newConversation(docFilter: DocumentScope): Conversation {
  return {
    id: crypto.randomUUID(),
    messages: [],
    docFilter,
    createdAt: new Date().toISOString(),
  };
}

export function useConversation() {
  const [conversations, setConversations] = useLocalStorage<Conversation[]>(
    STORAGE_KEY,
    []
  );
  const [activeId, setActiveId] = useLocalStorage<string | null>(
    ACTIVE_KEY,
    null
  );

  const active = conversations.find((c) => c.id === activeId) ?? null;

  const startConversation = useCallback(
    (docFilter: DocumentScope) => {
      const conv = newConversation(docFilter);
      setConversations((prev) => [...prev, conv]);
      setActiveId(conv.id);
      return conv;
    },
    [setConversations, setActiveId]
  );

  const addMessage = useCallback(
    (conversationId: string, message: Message) => {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === conversationId
            ? { ...c, messages: [...c.messages, message] }
            : c
        )
      );
    },
    [setConversations]
  );

  const updateMessage = useCallback(
    (conversationId: string, messageId: string, patch: Partial<Message>) => {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === conversationId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === messageId ? { ...m, ...patch } : m
                ),
              }
            : c
        )
      );
    },
    [setConversations]
  );

  const setFeedback = useCallback(
    (conversationId: string, messageId: string, rating: FeedbackRating) => {
      updateMessage(conversationId, messageId, { feedbackRating: rating });
    },
    [updateMessage]
  );

  const switchConversation = useCallback(
    (id: string) => setActiveId(id),
    [setActiveId]
  );

  return {
    conversations,
    active,
    startConversation,
    addMessage,
    updateMessage,
    setFeedback,
    switchConversation,
  };
}

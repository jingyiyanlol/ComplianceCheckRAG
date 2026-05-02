export type FeedbackRating = 1 | -1;

export interface Citation {
  chunk_id: string;
  doc_name: string;
  doc_title: string;
  section: string;
  score: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  feedbackRating?: FeedbackRating;
  isStreaming?: boolean;
}

export type DocumentScope = string[] | null; // null = all documents

export interface Conversation {
  id: string;
  messages: Message[];
  docFilter: DocumentScope;
  createdAt: string;
}

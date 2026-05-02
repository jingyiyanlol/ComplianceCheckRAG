import { ThumbsUp, ThumbsDown } from "lucide-react";
import { clsx } from "clsx";
import { submitFeedback } from "../lib/api";
import type { FeedbackRating } from "../types";

interface FeedbackButtonsProps {
  messageId: string;
  currentRating?: FeedbackRating;
  onRated: (rating: FeedbackRating) => void;
}

export function FeedbackButtons({
  messageId,
  currentRating,
  onRated,
}: FeedbackButtonsProps) {
  async function handleClick(rating: FeedbackRating) {
    if (currentRating !== undefined) return; // already rated
    onRated(rating); // optimistic update
    try {
      await submitFeedback(messageId, rating);
    } catch {
      // silently ignore network errors for feedback
    }
  }

  return (
    <div className="mt-1 flex gap-2">
      <button
        onClick={() => handleClick(1)}
        disabled={currentRating !== undefined}
        aria-label="Thumbs up"
        className={clsx(
          "flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg p-2 transition-colors",
          currentRating === 1
            ? "bg-green-100 text-green-600"
            : "text-gray-400 hover:bg-gray-100 hover:text-gray-600 disabled:cursor-default"
        )}
      >
        <ThumbsUp className="h-4 w-4" />
      </button>
      <button
        onClick={() => handleClick(-1)}
        disabled={currentRating !== undefined}
        aria-label="Thumbs down"
        className={clsx(
          "flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg p-2 transition-colors",
          currentRating === -1
            ? "bg-red-100 text-red-600"
            : "text-gray-400 hover:bg-gray-100 hover:text-gray-600 disabled:cursor-default"
        )}
      >
        <ThumbsDown className="h-4 w-4" />
      </button>
    </div>
  );
}

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { Citation } from "../types";

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export function CitationCard({ citation, index }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 text-xs">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex min-h-[44px] w-full items-center justify-between px-3 py-2 text-left"
        aria-expanded={expanded}
      >
        <span className="font-medium text-gray-700">
          [{index}] {citation.doc_name} — {citation.section}
        </span>
        {expanded ? (
          <ChevronUp className="h-4 w-4 shrink-0 text-gray-400" />
        ) : (
          <ChevronDown className="h-4 w-4 shrink-0 text-gray-400" />
        )}
      </button>
      {expanded && (
        <div className="border-t border-gray-200 px-3 py-2 text-gray-600">
          <p className="mb-1 text-gray-400">Score: {citation.score.toFixed(3)}</p>
          <p>{citation.doc_title}</p>
        </div>
      )}
    </div>
  );
}

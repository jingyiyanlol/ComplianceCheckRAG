import { useEffect, useState } from "react";
import { listDocuments } from "../lib/api";
import type { DocumentScope } from "../types";

interface ScopeModalProps {
  onStart: (scope: DocumentScope) => void;
}

export function ScopeModal({ onStart }: ScopeModalProps) {
  const [documents, setDocuments] = useState<string[]>([]);
  const [mode, setMode] = useState<"all" | "select">("all");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .finally(() => setLoading(false));
  }, []);

  function toggle(doc: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(doc) ? next.delete(doc) : next.add(doc);
      return next;
    });
  }

  function handleStart() {
    const scope: DocumentScope = mode === "all" ? null : Array.from(selected);
    onStart(scope);
  }

  const canStart = mode === "all" || selected.size > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 className="mb-1 text-lg font-semibold text-gray-900">
          Which documents should I search?
        </h2>
        <p className="mb-4 text-sm text-gray-500">
          This scope applies to the entire conversation.
        </p>

        <div className="mb-4 space-y-2">
          <label className="flex cursor-pointer items-center gap-3 rounded-lg border p-3 hover:bg-gray-50">
            <input
              type="radio"
              name="scope"
              checked={mode === "all"}
              onChange={() => setMode("all")}
              className="h-4 w-4 min-w-[1rem] accent-blue-600"
            />
            <div>
              <p className="font-medium text-gray-800">All documents</p>
              <p className="text-xs text-gray-500">Search across everything ingested</p>
            </div>
          </label>

          <label className="flex cursor-pointer items-center gap-3 rounded-lg border p-3 hover:bg-gray-50">
            <input
              type="radio"
              name="scope"
              checked={mode === "select"}
              onChange={() => setMode("select")}
              className="h-4 w-4 min-w-[1rem] accent-blue-600"
            />
            <div>
              <p className="font-medium text-gray-800">Select documents</p>
              <p className="text-xs text-gray-500">Restrict search to specific documents</p>
            </div>
          </label>
        </div>

        {mode === "select" && (
          <div className="mb-4 max-h-48 overflow-y-auto rounded-lg border p-2">
            {loading ? (
              <p className="p-2 text-sm text-gray-400">Loading documents…</p>
            ) : documents.length === 0 ? (
              <p className="p-2 text-sm text-gray-400">No documents ingested yet.</p>
            ) : (
              documents.map((doc) => (
                <label
                  key={doc}
                  className="flex cursor-pointer items-center gap-3 rounded p-2 hover:bg-gray-50"
                >
                  <input
                    type="checkbox"
                    checked={selected.has(doc)}
                    onChange={() => toggle(doc)}
                    className="h-4 w-4 min-w-[1rem] accent-blue-600"
                  />
                  <span className="truncate text-sm text-gray-700">{doc}</span>
                </label>
              ))
            )}
          </div>
        )}

        <button
          onClick={handleStart}
          disabled={!canStart}
          className="min-h-[44px] w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white
                     hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Start
        </button>
      </div>
    </div>
  );
}

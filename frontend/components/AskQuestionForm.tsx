"use client";

import { useState } from "react";
import { ApiError } from "@/lib/api";

export function AskQuestionForm({
  onAsk,
}: {
  onAsk: (questionText: string) => Promise<void>;
}) {
  const [questionText, setQuestionText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isAsking, setIsAsking] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!questionText.trim()) return;

    setError(null);
    setIsAsking(true);
    try {
      await onAsk(questionText);
      setQuestionText("");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not get an answer.",
      );
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Ask a question about this document…"
          value={questionText}
          onChange={(event) => setQuestionText(event.target.value)}
          disabled={isAsking}
          className="flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          disabled={isAsking || !questionText.trim()}
          className="rounded-full bg-black px-4 py-2 text-sm font-medium text-zinc-50 hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-50 dark:text-black dark:hover:bg-zinc-200"
        >
          {isAsking ? "Asking…" : "Ask"}
        </button>
      </div>
      {error ? (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      ) : null}
    </form>
  );
}

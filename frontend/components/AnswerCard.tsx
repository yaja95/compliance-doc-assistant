"use client";

import { useState } from "react";
import { ApiError, resolveReviewFlag } from "@/lib/api";
import type { QuestionAnswerRead, ReviewFlagRead } from "@/lib/types";

export interface Exchange {
  qa: QuestionAnswerRead;
  flag: ReviewFlagRead | null;
}

export function AnswerCard({
  exchange,
  onFlagUpdated,
}: {
  exchange: Exchange;
  onFlagUpdated: (flag: ReviewFlagRead) => void;
}) {
  const { qa, flag } = exchange;
  const [isResolving, setIsResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleResolve(status: "resolved" | "dismissed") {
    if (!flag) return;
    setError(null);
    setIsResolving(true);
    try {
      const updated = await resolveReviewFlag(flag.id, status);
      onFlagUpdated(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update the flag.");
    } finally {
      setIsResolving(false);
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <p className="text-sm font-medium text-black dark:text-zinc-50">
        {qa.question.question_text}
      </p>

      {qa.answer.needs_review && flag ? (
        <div className="flex flex-col gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950">
          <p className="font-medium text-amber-800 dark:text-amber-400">
            Needs human review
          </p>
          <p className="text-amber-700 dark:text-amber-500">
            {qa.answer.confidence_reason}
          </p>
          {flag.status === "pending" ? (
            <div className="flex gap-2">
              <button
                type="button"
                disabled={isResolving}
                onClick={() => handleResolve("resolved")}
                className="rounded-full bg-amber-800 px-3 py-1 text-xs font-medium text-amber-50 hover:bg-amber-900 disabled:opacity-50 dark:bg-amber-400 dark:text-black"
              >
                Mark resolved
              </button>
              <button
                type="button"
                disabled={isResolving}
                onClick={() => handleResolve("dismissed")}
                className="rounded-full border border-amber-800 px-3 py-1 text-xs font-medium text-amber-800 hover:bg-amber-100 disabled:opacity-50 dark:border-amber-400 dark:text-amber-400 dark:hover:bg-amber-900"
              >
                Dismiss
              </button>
            </div>
          ) : (
            <p className="text-xs text-amber-700 dark:text-amber-500">
              {flag.status === "resolved" ? "Resolved" : "Dismissed"}
              {flag.reviewed_at
                ? ` on ${new Date(flag.reviewed_at).toLocaleString()}`
                : ""}
            </p>
          )}
          {error ? (
            <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
          ) : null}
        </div>
      ) : null}

      <p className="text-sm text-zinc-700 dark:text-zinc-300">
        {qa.answer.answer_text}
      </p>

      {qa.answer.citations.length > 0 ? (
        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-500">
            Sources
          </p>
          <ul className="flex flex-col gap-1">
            {qa.answer.citations.map((citation) => (
              <li
                key={citation.chunk_id}
                className="rounded-md bg-zinc-100 px-3 py-2 text-xs text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400"
              >
                <span className="font-medium">
                  Chunk {citation.chunk_index}
                </span>{" "}
                (score {citation.relevance_score.toFixed(2)}): {citation.content}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

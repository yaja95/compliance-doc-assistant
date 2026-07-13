"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { StatusBadge } from "@/components/StatusBadge";
import { AskQuestionForm } from "@/components/AskQuestionForm";
import { AnswerCard, type Exchange } from "@/components/AnswerCard";
import { ApiError, askQuestion, getDocument, listReviewFlags } from "@/lib/api";
import type { DocumentDetailRead, ReviewFlagRead } from "@/lib/types";

function DocumentDetailContent({ documentId }: { documentId: number }) {
  const [document, setDocument] = useState<DocumentDetailRead | null>(null);
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDocument(documentId)
      .then(setDocument)
      .catch((err) =>
        setError(
          err instanceof ApiError ? err.message : "Could not load this document.",
        ),
      );
  }, [documentId]);

  async function handleAsk(questionText: string) {
    const qa = await askQuestion(documentId, questionText);

    let flag: ReviewFlagRead | null = null;
    if (qa.answer.needs_review) {
      const flags = await listReviewFlags();
      flag = flags.find((f) => f.answer_id === qa.answer.id) ?? null;
    }

    setExchanges((prev) => [{ qa, flag }, ...prev]);
  }

  function handleFlagUpdated(updated: ReviewFlagRead) {
    setExchanges((prev) =>
      prev.map((exchange) =>
        exchange.flag?.id === updated.id
          ? { ...exchange, flag: updated }
          : exchange,
      ),
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-12">
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-12">
        <p className="text-sm text-zinc-500">Loading…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-6 py-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">
            {document.filename}
          </h1>
          <p className="text-xs text-zinc-500 dark:text-zinc-500">
            {document.chunks.length} chunk
            {document.chunks.length === 1 ? "" : "s"}
          </p>
        </div>
        <StatusBadge status={document.status} />
      </div>

      {document.status === "embedded" ? (
        <AskQuestionForm onAsk={handleAsk} />
      ) : (
        <p className="text-sm text-zinc-500 dark:text-zinc-500">
          This document isn&apos;t ready for questions yet (status:{" "}
          {document.status}).
        </p>
      )}

      <div className="flex flex-col gap-4">
        {exchanges.map((exchange, index) => (
          <AnswerCard
            key={exchange.qa.question.id ?? index}
            exchange={exchange}
            onFlagUpdated={handleFlagUpdated}
          />
        ))}
      </div>
    </div>
  );
}

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const documentId = Number(params.id);

  return (
    <RequireAuth>
      <DocumentDetailContent documentId={documentId} />
    </RequireAuth>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { DocumentUploadForm } from "@/components/DocumentUploadForm";
import { StatusBadge } from "@/components/StatusBadge";
import { ApiError, listDocuments } from "@/lib/api";
import type { DocumentRead } from "@/lib/types";

function DocumentsPageContent() {
  const [documents, setDocuments] = useState<DocumentRead[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch((err) =>
        setError(
          err instanceof ApiError
            ? err.message
            : "Could not load documents.",
        ),
      );
  }, []);

  function handleUploaded(document: DocumentRead) {
    setDocuments((prev) => (prev ? [document, ...prev] : [document]));
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-6 py-12">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">
          Documents
        </h1>
      </div>

      <DocumentUploadForm onUploaded={handleUploaded} />

      {error ? (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      ) : null}

      {documents === null && !error ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : null}

      {documents !== null && documents.length === 0 ? (
        <p className="text-sm text-zinc-500 dark:text-zinc-500">
          No documents yet. Upload one to get started.
        </p>
      ) : null}

      {documents && documents.length > 0 ? (
        <ul className="flex flex-col divide-y divide-zinc-200 rounded-lg border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {documents.map((document) => (
            <li key={document.id}>
              <Link
                href={`/documents/${document.id}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-zinc-50 dark:hover:bg-zinc-900"
              >
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-black dark:text-zinc-50">
                    {document.filename}
                  </span>
                  <span className="text-xs text-zinc-500 dark:text-zinc-500">
                    {new Date(document.uploaded_at).toLocaleString()}
                  </span>
                </div>
                <StatusBadge status={document.status} />
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export default function DocumentsPage() {
  return (
    <RequireAuth>
      <DocumentsPageContent />
    </RequireAuth>
  );
}

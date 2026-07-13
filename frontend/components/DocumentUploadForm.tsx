"use client";

import { useRef, useState } from "react";
import { ApiError, uploadDocument } from "@/lib/api";
import type { DocumentRead } from "@/lib/types";

export function DocumentUploadForm({
  onUploaded,
}: {
  onUploaded: (document: DocumentRead) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setError(null);
    setIsUploading(true);
    try {
      const document = await uploadDocument(file);
      onUploaded(document);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Upload failed. Try again.",
      );
    } finally {
      setIsUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="flex w-fit cursor-pointer items-center gap-2 rounded-full bg-black px-4 py-2 text-sm font-medium text-zinc-50 hover:bg-zinc-800 dark:bg-zinc-50 dark:text-black dark:hover:bg-zinc-200">
        {isUploading ? "Uploading…" : "Upload document (.txt or .pdf)"}
        <input
          ref={inputRef}
          type="file"
          accept=".txt,.pdf"
          onChange={handleChange}
          disabled={isUploading}
          className="hidden"
        />
      </label>
      {error ? (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      ) : null}
    </div>
  );
}

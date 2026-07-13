import type { DocumentStatus } from "@/lib/types";

const STYLES: Record<DocumentStatus, string> = {
  embedded:
    "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-400",
  chunked: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400",
  pending: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-400",
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[status]}`}
    >
      {status}
    </span>
  );
}

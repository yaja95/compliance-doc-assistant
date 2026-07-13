"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function Home() {
  const { token } = useAuth();

  return (
    <div className="flex flex-1 items-center justify-center px-8 text-center">
      <div className="flex max-w-xl flex-col items-center gap-4">
        <h1 className="text-3xl font-semibold tracking-tight text-black dark:text-zinc-50">
          compliance-doc-assistant
        </h1>
        <p className="text-lg leading-8 text-zinc-600 dark:text-zinc-400">
          Upload a compliance document, ask questions, and get source-grounded
          answers with citations — flagged for human review when confidence
          is low.
        </p>
        <Link
          href={token ? "/documents" : "/login"}
          className="mt-2 rounded-full bg-black px-5 py-2 text-sm font-medium text-zinc-50 hover:bg-zinc-800 dark:bg-zinc-50 dark:text-black dark:hover:bg-zinc-200"
        >
          {token ? "Go to documents" : "Log in to get started"}
        </Link>
      </div>
    </div>
  );
}

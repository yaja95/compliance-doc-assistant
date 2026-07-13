"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(username, password);
      router.push("/documents");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Unable to log in right now.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-sm flex-col gap-6 px-6 py-16">
      <div>
        <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">
          Log in
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-500">
          Use the seeded demo account, or an account you&apos;ve created.
        </p>
      </div>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <label
            htmlFor="username"
            className="text-sm text-zinc-700 dark:text-zinc-300"
          >
            Username
          </label>
          <input
            id="username"
            name="username"
            type="text"
            required
            autoFocus
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label
            htmlFor="password"
            className="text-sm text-zinc-700 dark:text-zinc-300"
          >
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
        </div>
        {error ? (
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        ) : null}
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-full bg-black px-4 py-2 text-sm font-medium text-zinc-50 hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-50 dark:text-black dark:hover:bg-zinc-200"
        >
          {isSubmitting ? "Logging in…" : "Log in"}
        </button>
      </form>
    </div>
  );
}

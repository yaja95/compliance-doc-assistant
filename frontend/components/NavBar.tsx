"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export function NavBar() {
  const { user, token, logout } = useAuth();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800">
      <nav className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
        <Link href="/" className="font-semibold text-black dark:text-zinc-50">
          compliance-doc-assistant
        </Link>
        <div className="flex items-center gap-4 text-sm">
          {token ? (
            <>
              <Link
                href="/documents"
                className="text-zinc-600 hover:text-black dark:text-zinc-400 dark:hover:text-zinc-50"
              >
                Documents
              </Link>
              {user ? (
                <span className="text-zinc-500 dark:text-zinc-500">
                  {user.username}
                </span>
              ) : null}
              <button
                type="button"
                onClick={handleLogout}
                className="rounded-full border border-zinc-300 px-3 py-1 text-zinc-700 hover:border-zinc-400 dark:border-zinc-700 dark:text-zinc-300 dark:hover:border-zinc-600"
              >
                Log out
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded-full bg-black px-3 py-1 text-zinc-50 hover:bg-zinc-800 dark:bg-zinc-50 dark:text-black dark:hover:bg-zinc-200"
            >
              Log in
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}

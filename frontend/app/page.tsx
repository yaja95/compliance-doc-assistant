export default function Home() {
  return (
    <div className="flex flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex max-w-xl flex-col gap-4 px-8 text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-black dark:text-zinc-50">
          compliance-doc-assistant
        </h1>
        <p className="text-lg leading-8 text-zinc-600 dark:text-zinc-400">
          Upload a compliance document, ask questions, and get source-grounded
          answers with citations — flagged for human review when confidence
          is low.
        </p>
        <p className="text-sm text-zinc-500 dark:text-zinc-500">
          Under construction.
        </p>
      </main>
    </div>
  );
}

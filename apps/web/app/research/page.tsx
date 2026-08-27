import Link from "next/link";
import { ResearchPanel } from "@/components/ResearchPanel";

export default function ResearchPage() {
  return (
    <main className="flex min-h-screen flex-col items-center gap-8 bg-zinc-50 px-6 py-16 dark:bg-black">
      <div className="flex w-full max-w-2xl flex-col gap-2">
        <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300">
          ← Home
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
          Deep Research
        </h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Multi-source research reports — the agent searches documents, tenders, and
          knowledge-graph entities together, citing every claim against what it actually retrieved.
        </p>
      </div>
      <div className="w-full max-w-2xl">
        <ResearchPanel />
      </div>
    </main>
  );
}

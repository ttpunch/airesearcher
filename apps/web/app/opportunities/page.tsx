import Link from "next/link";
import { OpportunitiesPanel } from "@/components/OpportunitiesPanel";

export default function OpportunitiesPage() {
  return (
    <main className="flex min-h-screen flex-col items-center gap-8 bg-zinc-50 px-6 py-16 dark:bg-black">
      <div className="flex w-full max-w-2xl flex-col gap-2">
        <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300">
          ← Home
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
          Opportunities
        </h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          The strategy report&apos;s Top 10 strategic initiatives, ranked by weighted score.
          Recommendation-tagged — nothing here acts until a human approves it.
        </p>
      </div>
      <div className="w-full max-w-2xl">
        <OpportunitiesPanel />
      </div>
    </main>
  );
}

import { StatusCard } from "@/components/StatusCard";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-zinc-50 px-6 text-center dark:bg-black">
      <h1 className="text-3xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
        airesearcher
      </h1>
      <p className="max-w-md text-lg text-zinc-600 dark:text-zinc-400">
        A BHEL public-data-first AI research and intelligence platform.
      </p>
      <div className="w-full max-w-sm text-left">
        <StatusCard />
      </div>
    </main>
  );
}

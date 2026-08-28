"use client";

import { useState, type FormEvent } from "react";
import { Markdown } from "@/components/Markdown";
import { askQuestion, type AskResponse } from "@/lib/api";

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "done"; result: AskResponse };

function TierBadge({ tier }: { tier: string }) {
  return (
    <span className="inline-flex items-center rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
      {tier}
    </span>
  );
}

function VerifiedBadge({ verified, unverifiableCount }: { verified: boolean; unverifiableCount: number }) {
  if (verified) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800 dark:bg-green-950 dark:text-green-300">
        <span className="h-2 w-2 rounded-full bg-green-500" />
        Verified — every citation grounded
      </span>
    );
  }
  if (unverifiableCount > 0) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-800 dark:bg-red-950 dark:text-red-300">
        <span className="h-2 w-2 rounded-full bg-red-500" />
        {unverifiableCount} citation{unverifiableCount === 1 ? "" : "s"} could not be verified
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-3 py-1 text-sm font-medium text-amber-800 dark:bg-amber-950 dark:text-amber-300">
      <span className="h-2 w-2 rounded-full bg-amber-500" />
      No citations — not verified
    </span>
  );
}

export function AskPanel() {
  const [question, setQuestion] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;

    setState({ kind: "loading" });
    try {
      const result = await askQuestion(trimmed);
      setState({ kind: "done", result });
    } catch (err) {
      setState({ kind: "error", message: err instanceof Error ? err.message : "Unknown error" });
    }
  }

  return (
    <div className="flex w-full flex-col gap-6">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label htmlFor="question" className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
          Ask about BHEL
        </label>
        <div className="flex gap-2">
          <input
            id="question"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What power generation equipment does BHEL manufacture?"
            className="flex-1 rounded-lg border border-zinc-200 bg-white px-4 py-2.5 text-sm text-zinc-950 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-50"
          />
          <button
            type="submit"
            disabled={state.kind === "loading" || !question.trim()}
            className="rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-50 dark:text-zinc-950 dark:hover:bg-zinc-300"
          >
            {state.kind === "loading" ? "Researching…" : "Ask"}
          </button>
        </div>
        <p className="text-xs text-zinc-500 dark:text-zinc-500">
          Answers are grounded only in indexed public sources. Every factual claim is expected to
          carry a [chunk:id] citation you can verify below.
        </p>
      </form>

      {state.kind === "loading" && (
        <p className="text-sm text-zinc-500">Searching indexed sources and drafting an answer…</p>
      )}

      {state.kind === "error" && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {state.message}
        </div>
      )}

      {state.kind === "done" && (
        <div className="flex flex-col gap-4 rounded-lg border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
          <VerifiedBadge
            verified={state.result.verified}
            unverifiableCount={state.result.unverifiable_citation_count}
          />
          <Markdown>{state.result.answer}</Markdown>

          {state.result.citations.length > 0 && (
            <div className="flex flex-col gap-2 border-t border-zinc-100 pt-4 dark:border-zinc-900">
              <h3 className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-500">
                Sources
              </h3>
              <ul className="flex flex-col gap-3">
                {state.result.citations.map((c) => (
                  <li
                    key={c.chunk_id}
                    className="flex flex-col gap-1 rounded-md bg-zinc-50 p-3 text-sm dark:bg-zinc-900"
                  >
                    <div className="flex items-center gap-2">
                      <TierBadge tier={c.source_tier} />
                      <a
                        href={c.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-zinc-900 underline decoration-zinc-300 hover:decoration-zinc-500 dark:text-zinc-100 dark:decoration-zinc-700"
                      >
                        {c.source_name}
                      </a>
                      <span className="text-xs text-zinc-400">[chunk:{c.chunk_id}]</span>
                    </div>
                    <p className="text-zinc-600 dark:text-zinc-400">{c.content}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

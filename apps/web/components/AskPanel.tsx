"use client";

import { useState, type FormEvent } from "react";
import { askQuestion, type AskResponse } from "@/lib/api";
import { IconCheck } from "@/components/icons";

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "done"; result: AskResponse };

function TierBadge({ tier }: { tier: string }) {
  return (
    <span className="inline-flex items-center rounded border border-info/35 bg-info/14 px-1.5 py-0.5 font-mono text-[10px] font-medium text-info">
      {tier}
    </span>
  );
}

function VerifiedBadge({ verified, unverifiableCount }: { verified: boolean; unverifiableCount: number }) {
  if (verified) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded border border-ok/35 bg-ok/14 px-3 py-1 font-mono text-[11px] font-medium tracking-wide text-ok uppercase">
        <IconCheck className="h-[11px] w-[11px]" />
        Verified — every citation grounded
      </span>
    );
  }
  if (unverifiableCount > 0) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded border border-err/35 bg-err/14 px-3 py-1 font-mono text-[11px] font-medium tracking-wide text-err uppercase">
        <span className="h-2 w-2 rounded-full bg-err" />
        {unverifiableCount} citation{unverifiableCount === 1 ? "" : "s"} could not be verified
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded border border-warn/35 bg-warn/14 px-3 py-1 font-mono text-[11px] font-medium tracking-wide text-warn uppercase">
      <span className="h-2 w-2 rounded-full bg-warn" />
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
    <div className="flex w-full max-w-3xl flex-col gap-6">
      <form onSubmit={handleSubmit} className="flex flex-col gap-2.5">
        <label htmlFor="question" className="text-xs font-medium text-ink-muted">
          Ask about BHEL
        </label>
        <div className="flex gap-2.5">
          <input
            id="question"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What power generation equipment does BHEL manufacture?"
            className="flex-1 rounded border border-line bg-inset px-3.5 py-3 text-[13.5px] text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-accent/40"
          />
          <button
            type="submit"
            disabled={state.kind === "loading" || !question.trim()}
            className="rounded bg-accent px-5 font-semibold text-[13.5px] text-ink-onaccent disabled:cursor-not-allowed disabled:opacity-50"
          >
            {state.kind === "loading" ? "Researching…" : "Ask"}
          </button>
        </div>
        <p className="text-xs text-ink-faint">
          Answers are grounded only in indexed public sources. Every factual claim is expected to
          carry a [chunk:id] citation you can verify below.
        </p>
      </form>

      {state.kind === "loading" && <p className="text-sm text-ink-muted">Searching indexed sources and drafting an answer…</p>}

      {state.kind === "error" && (
        <div className="rounded-md border border-err/35 bg-err/10 p-4 text-sm text-err">{state.message}</div>
      )}

      {state.kind === "done" && (
        <div className="flex flex-col gap-4 rounded-md border border-line bg-surface p-5.5">
          <VerifiedBadge
            verified={state.result.verified}
            unverifiableCount={state.result.unverifiable_citation_count}
          />
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-muted">{state.result.answer}</p>

          {state.result.citations.length > 0 && (
            <div className="flex flex-col gap-2 border-t border-line pt-4">
              <h3 className="font-mono text-[11px] tracking-wide text-ink-faint uppercase">Sources</h3>
              <ul className="flex flex-col gap-2">
                {state.result.citations.map((c) => (
                  <li key={c.chunk_id} className="flex flex-col gap-1.5 rounded border border-line bg-inset p-3.5 text-sm">
                    <div className="flex items-center gap-2">
                      <TierBadge tier={c.source_tier} />
                      <a
                        href={c.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-ink underline decoration-line-strong hover:decoration-accent"
                      >
                        {c.source_name}
                      </a>
                      <span className="ml-auto font-mono text-[10.5px] text-ink-faint">[chunk:{c.chunk_id}]</span>
                    </div>
                    <p className="text-[12.5px] leading-relaxed text-ink-faint">{c.content}</p>
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

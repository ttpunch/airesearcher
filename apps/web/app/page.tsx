import Link from "next/link";
import type { ReactNode } from "react";
import { StatusCard } from "@/components/StatusCard";
import { NAV_LINKS } from "@/lib/nav";
import {
  LogoMark,
  IconAsk,
  IconResearch,
  IconTenders,
  IconOpportunities,
} from "@/components/icons";

const HOME_HINTS: Record<string, string> = {
  "/ask": "Citation-verified Q&A over public sources",
  "/research": "Multi-source-class reports, cited by type",
  "/tenders": "Discovery, extraction, bid-pattern analysis",
  "/opportunities": "Top 10 initiatives, human-approved",
};

const HOME_ICONS: Record<string, (props: { className?: string }) => ReactNode> = {
  "/ask": IconAsk,
  "/research": IconResearch,
  "/tenders": IconTenders,
  "/opportunities": IconOpportunities,
};

const FEATURED_LINKS = NAV_LINKS.filter((link) => link.href in HOME_HINTS);

export default function Home() {
  return (
    <main
      className="flex min-h-screen flex-col items-center gap-8 px-6 py-24 text-center"
      style={{
        backgroundImage:
          "linear-gradient(color-mix(in oklch, white 3.5%, transparent) 1px, transparent 1px), linear-gradient(90deg, color-mix(in oklch, white 3.5%, transparent) 1px, transparent 1px)",
        backgroundSize: "36px 36px",
      }}
    >
      <LogoMark className="h-14 w-14 text-accent" />
      <div className="font-mono text-[11.5px] tracking-[0.12em] text-ink-faint uppercase">
        Public-data-first <span className="text-accent">·</span> BHEL Intelligence
      </div>
      <h1 className="font-display text-4xl font-semibold tracking-tight text-ink lg:text-5xl">
        airesearcher
      </h1>
      <p className="max-w-lg text-base leading-relaxed text-ink-muted">
        A BHEL public-data-first AI research and intelligence platform. Every factual claim is
        traceable to a tiered source — or the system says it cannot verify it.
      </p>

      <div className="flex items-center gap-3.5">
        <Link
          href="/dashboard"
          className="rounded bg-accent px-6 py-3 text-sm font-semibold text-ink-onaccent"
        >
          Open Dashboard →
        </Link>
        <Link
          href="/ask"
          className="rounded border border-line-strong px-5 py-3 text-sm font-medium text-ink"
        >
          Ask a question
        </Link>
      </div>

      <div className="mt-2 grid w-full max-w-3xl grid-cols-2 gap-3 text-left lg:grid-cols-4">
        {FEATURED_LINKS.map((link) => {
          const Icon = HOME_ICONS[link.href];
          return (
            <Link
              key={link.href}
              href={link.href}
              className="flex flex-col gap-2.5 rounded-md border border-line bg-surface p-4"
            >
              {Icon && <Icon className="h-5 w-5 text-accent" />}
              <span className="text-sm font-semibold text-ink">{link.label}</span>
              <span className="text-[11.5px] leading-tight text-ink-faint">{HOME_HINTS[link.href]}</span>
            </Link>
          );
        })}
      </div>

      <div className="mt-6 w-full max-w-sm text-left">
        <StatusCard />
      </div>
    </main>
  );
}

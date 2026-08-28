"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { fetchStatus, type StatusResponse } from "@/lib/api";
import { NAV_LINKS } from "@/lib/nav";
import {
  LogoMark,
  IconDashboard,
  IconAsk,
  IconResearch,
  IconTenders,
  IconCompetitors,
  IconTechnologies,
  IconOpportunities,
  IconGraph,
  IconMenu,
  IconClose,
} from "@/components/icons";

const NAV_ICONS: Record<string, (props: { className?: string }) => ReactNode> = {
  "/dashboard": IconDashboard,
  "/ask": IconAsk,
  "/research": IconResearch,
  "/tenders": IconTenders,
  "/competitors": IconCompetitors,
  "/technologies": IconTechnologies,
  "/opportunities": IconOpportunities,
  "/graph": IconGraph,
};

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2.5 px-2">
      <LogoMark className="h-[30px] w-[30px] shrink-0 text-accent" />
      <span className="flex flex-col leading-tight">
        <span className="font-display text-base font-semibold text-ink">airesearcher</span>
        <span className="font-mono text-[9.5px] tracking-[0.09em] text-ink-faint uppercase">
          BHEL Intelligence
        </span>
      </span>
    </Link>
  );
}

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-0.5">
      {NAV_LINKS.map((link) => {
        const Icon = NAV_ICONS[link.href];
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            onClick={onNavigate}
            className={`flex items-center gap-2.5 rounded border-l-[3px] px-3 py-2 text-[13.5px] font-medium ${
              active
                ? "border-l-accent bg-accent/14 text-ink"
                : "border-l-transparent text-ink-muted hover:text-ink"
            }`}
          >
            {Icon && <Icon className={`h-[18px] w-[18px] shrink-0 ${active ? "text-accent" : "text-ink-faint"}`} />}
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

function StatusFooter() {
  const [status, setStatus] = useState<StatusResponse | null>(null);

  useEffect(() => {
    fetchStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  const apiOk = status?.api === "ok";
  const dbOk = status?.db === "ok";

  return (
    <div className="mt-auto flex flex-col gap-2 border-t border-line pt-4">
      <div className="flex items-center justify-between px-2">
        <span className="flex items-center gap-1.5 text-xs text-ink-muted">
          <span className={`h-[7px] w-[7px] rounded-full ring-3 ${apiOk ? "bg-ok ring-ok/20" : "bg-err ring-err/20"}`} />
          API
        </span>
      </div>
      <div className="flex items-center justify-between px-2">
        <span className="flex items-center gap-1.5 text-xs text-ink-muted">
          <span className={`h-[7px] w-[7px] rounded-full ring-3 ${dbOk ? "bg-ok ring-ok/20" : "bg-err ring-err/20"}`} />
          Database
        </span>
      </div>
      {status && <div className="px-2 font-mono text-[10px] text-ink-faint">{status.timestamp}</div>}
    </div>
  );
}

export function AppShell({
  breadcrumb,
  title,
  description,
  action,
  children,
}: {
  breadcrumb: string;
  title: string;
  description: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar */}
      <aside className="hidden w-[248px] shrink-0 flex-col gap-6 border-r border-line bg-sidebar p-3.5 lg:flex">
        <Brand />
        <NavList />
        <StatusFooter />
      </aside>

      {/* Mobile top app bar */}
      <div className="fixed inset-x-0 top-0 z-40 flex items-center gap-3 border-b border-line bg-sidebar px-4 py-3.5 lg:hidden">
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          aria-label="Open navigation"
          className="flex h-9 w-9 items-center justify-center text-ink-muted"
        >
          <IconMenu className="h-[22px] w-[22px]" />
        </button>
        <Link href="/" className="flex items-center gap-2">
          <LogoMark className="h-[22px] w-[22px] text-accent" />
          <span className="font-display text-sm font-semibold text-ink">airesearcher</span>
        </Link>
      </div>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            className="absolute inset-0 bg-black/60"
            onClick={() => setDrawerOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 flex w-[260px] flex-col gap-6 bg-sidebar p-3.5">
            <div className="flex items-center justify-between">
              <Brand />
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                aria-label="Close navigation"
                className="flex h-9 w-9 items-center justify-center text-ink-muted"
              >
                <IconClose className="h-5 w-5" />
              </button>
            </div>
            <NavList onNavigate={() => setDrawerOpen(false)} />
            <StatusFooter />
          </div>
        </div>
      )}

      <main className="flex-1 min-w-0 px-6 py-9 pt-24 lg:px-11 lg:py-9">
        <div className="mb-7 flex max-w-[860px] items-start justify-between gap-6">
          <div>
            <div className="mb-2.5 font-mono text-[11px] tracking-[0.08em] text-ink-faint uppercase">
              PLATFORM / <span className="text-accent">{breadcrumb}</span>
            </div>
            <h1 className="mb-2 font-display text-[28px] font-semibold tracking-tight text-ink lg:text-[30px]">
              {title}
            </h1>
            <p className="max-w-[620px] text-sm leading-relaxed text-ink-muted">{description}</p>
          </div>
          {action}
        </div>
        {children}
      </main>
    </div>
  );
}

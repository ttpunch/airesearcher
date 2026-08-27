// Inline stroke icons (20x20 viewBox, currentColor) — matches the approved
// design canvas exactly. One consistent style; never emoji/dingbats.
// Each accepts standard SVG props so callers can set className for sizing.

import type { SVGProps } from "react";

export function LogoMark(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 32 32" fill="none" {...props}>
      <path
        d="M16 3 27 9.5v13L16 29 5 22.5v-13L16 3Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <circle cx="16" cy="16" r="3.2" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M16 3v9.8M27 9.5l-8.4 5M5 9.5l8.4 5M16 29v-9.8M27 22.5l-8.4-5M5 22.5l8.4-5"
        stroke="currentColor"
        strokeWidth="1.2"
        opacity="0.5"
      />
    </svg>
  );
}

export function IconDashboard(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" {...props}>
      <rect x="2.5" y="2.5" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.6" />
      <rect x="11.5" y="2.5" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.6" />
      <rect x="2.5" y="11.5" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.6" />
      <rect x="11.5" y="11.5" width="6" height="6" rx="1" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

export function IconAsk(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" {...props}>
      <path
        d="M3 5.5C3 4.67 3.67 4 4.5 4h11c.83 0 1.5.67 1.5 1.5v6c0 .83-.67 1.5-1.5 1.5H9l-3.5 3v-3H4.5C3.67 13 3 12.33 3 11.5v-6Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function IconResearch(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" {...props}>
      <path
        d="M5 3h6l3 3v9a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M7 8h4M7 11h3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="13.5" cy="13.5" r="2.6" stroke="currentColor" strokeWidth="1.5" />
      <path d="M15.6 15.6 17.5 17.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function IconTenders(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" {...props}>
      <path
        d="M5 2.5h7l3 3v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-13a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M7 8h6M7 11h6M7 14h4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

export function IconCompetitors(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" {...props}>
      <rect x="3" y="6" width="6" height="11" stroke="currentColor" strokeWidth="1.5" />
      <rect x="11" y="3" width="6" height="14" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M5 9h2M5 12h2M13 6h2M13 9h2M13 12h2"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function IconTechnologies(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" {...props}>
      <rect x="5.5" y="5.5" width="9" height="9" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M8 5.5V3M12 5.5V3M8 17v-2.5M12 17v-2.5M5.5 8H3M5.5 12H3M17 8h-2.5M17 12h-2.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function IconOpportunities(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" {...props}>
      <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="10" cy="10" r="3.6" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="10" cy="10" r="0.9" fill="currentColor" />
    </svg>
  );
}

export function IconGraph(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" {...props}>
      <circle cx="5" cy="5" r="2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="15" cy="5" r="2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="10" cy="15" r="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M6.6 6.2 8.6 13.2M13.4 6.2 11.4 13.2M7 5h6" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}

export function IconMenu(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" {...props}>
      <path d="M3 5.5h14M3 10h14M3 14.5h14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function IconClose(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" {...props}>
      <path d="M5 5l10 10M15 5 5 15" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function IconCheck(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" {...props}>
      <path d="M4 10.5 8 14.5 16 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

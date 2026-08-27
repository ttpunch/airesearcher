export type NavLink = {
  href: string;
  label: string;
};

// Central list so each week's new page just adds one entry here instead of
// editing the home page's markup directly.
export const NAV_LINKS: NavLink[] = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/ask", label: "Ask AI" },
  { href: "/research", label: "Deep Research" },
  { href: "/tenders", label: "Tenders" },
  { href: "/competitors", label: "Competitors" },
  { href: "/technologies", label: "Technologies" },
  { href: "/opportunities", label: "Opportunities" },
  { href: "/graph", label: "Knowledge Graph" },
];

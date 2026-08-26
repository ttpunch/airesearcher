export function getApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

export type StatusResponse = {
  api: string;
  db: string;
  timestamp: string;
};

export async function fetchStatus(): Promise<StatusResponse> {
  const res = await fetch(`${getApiUrl()}/api/status`);
  if (!res.ok) {
    throw new Error(`Status request failed: ${res.status}`);
  }
  return res.json();
}

export type Citation = {
  chunk_id: number;
  content: string;
  source_name: string;
  source_url: string;
  source_tier: string;
  document_id: number;
};

export type AskResponse = {
  answer: string;
  citations: Citation[];
  unverifiable_citation_count: number;
  verified: boolean;
};

export async function askQuestion(question: string): Promise<AskResponse> {
  const res = await fetch(`${getApiUrl()}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Ask request failed: ${res.status}`);
  }
  return res.json();
}

export type Tender = {
  id: number;
  source_id: number;
  document_id: number | null;
  title: string;
  tender_ref: string | null;
  organization: string;
  url: string;
  published_date: string | null;
  closing_date: string | null;
  estimated_value: string | null;
  status: string;
  extracted_requirements: string | null;
  created_at: string;
};

export type TenderAnalysis = {
  total_tenders: number;
  by_status: Record<string, number>;
  by_organization: { organization: string; total: number; by_status: Record<string, number> }[];
};

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${getApiUrl()}${path}`);
  if (!res.ok) {
    throw new Error(`Request to ${path} failed: ${res.status}`);
  }
  return res.json();
}

export function fetchTenders(): Promise<Tender[]> {
  return getJson<Tender[]>("/api/tenders");
}

export function fetchTenderAnalysis(): Promise<TenderAnalysis> {
  return getJson<TenderAnalysis>("/api/tenders/analyze");
}

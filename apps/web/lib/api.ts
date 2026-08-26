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

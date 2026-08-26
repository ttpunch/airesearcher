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

export type Entity = {
  id: number;
  name: string;
  entity_type: string;
  description: string | null;
  source_id: number | null;
  source_name: string | null;
  source_url: string | null;
  created_at: string;
};

export function fetchEntities(entityType: string): Promise<Entity[]> {
  return getJson<Entity[]>(`/api/entities?entity_type=${encodeURIComponent(entityType)}`);
}

export type Reference = {
  ref_type: string;
  ref_id: number;
  label: string;
  detail: string | null;
  url: string | null;
  tier: string | null;
};

export type ResearchReport = {
  id: number;
  topic: string;
  summary: string;
  references: Reference[];
  unverifiable_reference_count: number;
  status: string;
  created_at: string;
};

export function fetchResearchReports(): Promise<ResearchReport[]> {
  return getJson<ResearchReport[]>("/api/research");
}

export async function createResearchReport(topic: string): Promise<ResearchReport> {
  const res = await fetch(`${getApiUrl()}/api/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Research request failed: ${res.status}`);
  }
  return res.json();
}

export type Opportunity = {
  id: number;
  title: string;
  description: string;
  feasibility: string;
  strategic_value: string;
  weighted_score: number;
  tech_summary: string;
  timeline: string;
  risk: string;
  source_section: string;
  status: string;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
};

export function fetchOpportunities(): Promise<Opportunity[]> {
  return getJson<Opportunity[]>("/api/opportunities");
}

async function decideOpportunity(id: number, action: "approve" | "reject", approvedBy: string): Promise<Opportunity> {
  const res = await fetch(`${getApiUrl()}/api/opportunities/${id}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved_by: approvedBy }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Opportunity ${action} failed: ${res.status}`);
  }
  return res.json();
}

export function approveOpportunity(id: number, approvedBy: string): Promise<Opportunity> {
  return decideOpportunity(id, "approve", approvedBy);
}

export function rejectOpportunity(id: number, approvedBy: string): Promise<Opportunity> {
  return decideOpportunity(id, "reject", approvedBy);
}

export type Relationship = {
  id: number;
  from_entity_id: number;
  to_entity_id: number;
  from_entity_name: string;
  to_entity_name: string;
  relation_type: string;
  description: string | null;
  created_at: string;
};

export function fetchAllEntities(): Promise<Entity[]> {
  return getJson<Entity[]>("/api/entities");
}

export function fetchRelationships(): Promise<Relationship[]> {
  return getJson<Relationship[]>("/api/relationships");
}

export type DashboardSummary = {
  counts: {
    sources: number;
    documents: number;
    chunks: number;
    tenders: number;
    entities: number;
    research_reports: number;
    opportunities: number;
  };
  top_opportunities: Opportunity[];
};

export function fetchDashboardSummary(): Promise<DashboardSummary> {
  return getJson<DashboardSummary>("/api/dashboard/summary");
}

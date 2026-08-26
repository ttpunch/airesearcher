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

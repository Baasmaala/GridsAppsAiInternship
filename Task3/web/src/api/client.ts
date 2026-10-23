// small fetch helpers. vite passes /api to the backend on 127.0.0.1:8001.

export type WorkflowNode = { id: string; type: string };

export type WorkflowSummary = { key: string; id: string | null; ok: boolean; errors: string[] };

export type WorkflowDetail = WorkflowSummary & {
  raw: unknown;
  version?: string;
  allowed_languages?: string[];
  nodes?: WorkflowNode[];
  edges?: [string, string][];
  mermaid?: string;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function getJson<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { headers: { Accept: 'application/json' } });
  } catch {
    throw new ApiError(0, 'no connection');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  workflows: () => getJson<WorkflowSummary[]>('/api/workflows'),
  workflow: (key: string) => getJson<WorkflowDetail>(`/api/workflows/${encodeURIComponent(key)}`),
};

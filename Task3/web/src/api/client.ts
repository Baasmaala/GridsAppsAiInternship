// small fetch helpers. vite passes /api to the backend on 127.0.0.1:8001.

import type { AskSource, ChatBody } from '../lib/ask';

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

export type Attempt = { attempt: number; error?: string; wait_s?: number; result?: string };

export type TraceEntry = {
  node: string;
  type: string;
  input: unknown;
  output?: unknown;
  ms: number;
  result: 'ok' | 'stop' | 'error';
  status?: string;
  note?: string;
  error?: string;
  attempts?: Attempt[];
};

export type Item = {
  source_id: unknown;
  status: string;
  steps: string[];
  word_count?: number;
  possible_duplicate_of?: string;
  error?: string;
  trace: TraceEntry[];
};

export type Report = {
  run_id: string;
  workflow_id: string;
  workflow_version?: string;
  generated_at: string;
  mode: 'dry-run' | 'review' | 'approved';
  summary: Record<string, number>;
  items: Item[];
};

export type RunSummary = {
  run_id: string;
  created_at: string;
  workflow_id: string;
  mode: Report['mode'];
  summary: Record<string, number>;
  waiting: Record<string, string>;
};

export type RunDetail = {
  run_id: string;
  created_at: string;
  updated_at: string;
  workflow_id: string;
  report: Report;
  waiting: Record<string, string>;
};

export type Sample = { key: string; source: 'built-in' | 'upload'; items: number };

export type Record_ = Record<string, unknown>;

export type ReviewItem = {
  run_id: string;
  workflow_id: string;
  source_id: string;
  status: string;
  created_at: string;
  original: unknown;
  normalized: Record_;
  word_count?: number | null;
  possible_duplicate_of?: string | null;
  old_draft?: Record_ | null;
};

export type DecisionResult = {
  run_id: string;
  decision: 'approve' | 'reject';
  reviewer: string;
  items: { source_id: string; status: string }[];
  still_waiting: Record<string, string>;
};

export type DraftRow = { file: string; draft: Record_ };

export type AuditLine = {
  seq: number;
  time: string;
  event: string;
  run_id: string;
  workflow_id: string;
  source_id: unknown;
  status: string;
  reviewer?: string;
  reason?: string;
  duplicate_of?: string;
  prev_hash: string;
  hash: string;
};

export type Verify = { ok: boolean; lines: number; broken_line?: number; reason?: string; note?: string };

export type Challenge = { number: number; name: string; what: string; expected: string; got: string; passed: boolean };

export class ApiError extends Error {
  constructor(public status: number, message: string, public errors: string[] = []) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { ...init, headers: { Accept: 'application/json', ...(init?.headers ?? {}) } });
  } catch {
    throw new ApiError(0, 'no connection');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === 'string' ? body.detail
      : Array.isArray(body.detail) ? body.detail.map((d: { msg?: string }) => d.msg).join('; ') : res.statusText;
    throw new ApiError(res.status, detail, Array.isArray(body.errors) ? body.errors : []);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  call<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  workflows: () => call<WorkflowSummary[]>('/api/workflows'),
  workflow: (key: string) => call<WorkflowDetail>(`/api/workflows/${encodeURIComponent(key)}`),
  samples: () => call<Sample[]>('/api/samples'),
  upload: (name: string, text: string) =>
    call<{ key: string; items: number }>(`/api/samples/upload?name=${encodeURIComponent(name)}`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: text }),
  run: (body: { workflow: string; sample: string; dry_run: boolean; approved_by?: string }) =>
    post<Report>('/api/runs', body),
  runs: () => call<RunSummary[]>('/api/runs'),
  runDetail: (id: string) => call<RunDetail>(`/api/runs/${encodeURIComponent(id)}`),
  reviews: () => call<ReviewItem[]>('/api/reviews'),
  decide: (runId: string, sid: string, body: { reviewer: string; decision: 'approve' | 'reject'; reason?: string }) =>
    post<DecisionResult>(`/api/reviews/${encodeURIComponent(runId)}/${encodeURIComponent(sid)}`, body),
  drafts: () => call<DraftRow[]>('/api/drafts'),
  audit: () => call<AuditLine[]>('/api/audit'),
  verify: () => call<Verify>('/api/audit/verify'),
  challenges: () => post<{ passed: number; total: number; results: Challenge[] }>('/api/challenges/run'),
  chat: (body: ChatBody) => post<{ answer: string; source: AskSource; kind: string }>('/api/ask', body),
  reset: (seed: boolean) =>
    post<{ cleared: boolean; seeded: { run_id: string; summary: Record<string, number> } | null }>(
      '/api/demo/reset', { confirm: 'reset', seed }),
};

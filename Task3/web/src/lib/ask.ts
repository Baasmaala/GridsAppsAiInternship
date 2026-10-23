import type { Item } from '../api/client';
import type { Lang } from '../i18n/strings';

export type AskContext =
  | { kind: 'run'; runId: string; index: number }
  | { kind: 'dry'; item: Item; workflow: string; sourceId: string }
  | { kind: 'none' };

export type ChatBody = {
  question: string;
  lang: Lang;
  run_id?: string;
  index?: number;
  item?: Item;
  workflow?: string;
};

type Last = { report: { items: Item[] }; workflowKey: string } | null;

// what the panel is looking at comes from the page you are on (Replay has a run and a lesson)
export function askContext(page: string, params: URLSearchParams, last: Last): AskContext {
  if (page !== 'replay') return { kind: 'none' };
  const run = params.get('run') ?? (last ? 'dry' : null);
  const index = Number(params.get('i') ?? '0') || 0;
  if (run === 'dry') {
    const item = last?.report.items[index];
    return item ? { kind: 'dry', item, workflow: last!.workflowKey, sourceId: String(item.source_id) } : { kind: 'none' };
  }
  return run ? { kind: 'run', runId: run, index } : { kind: 'none' };
}

export function askBody(question: string, lang: Lang, ctx: AskContext): ChatBody {
  const body: ChatBody = { question: question.trim(), lang };
  if (ctx.kind === 'run') Object.assign(body, { run_id: ctx.runId, index: ctx.index });
  // a dry run is never saved, so the lesson goes with the question (only as data)
  if (ctx.kind === 'dry') Object.assign(body, { item: ctx.item, workflow: ctx.workflow });
  return body;
}

export type AskSource = { run: string | null; lesson: string | null; station: string | null; mode: string };

// "run" only goes in front of a real run id, not in front of "dry run" or "what-if dry run"
const runPart = (run: string | null) => (run && /^[0-9a-f]{8}$/.test(run) ? `run ${run}` : run);

export const sourceLine = (s: AskSource) => [runPart(s.run), s.lesson, s.station, s.mode].filter(Boolean).join(' · ');

import { en, type Key } from '../i18n/strings';

type T = (key: Key, vars?: Record<string, string | number>) => string;

const has = (key: string): key is Key => key in en;

// workflow file key or workflow id -> a name people read
const BY_ID: Record<string, string> = {
  'dorosak-content-intake': 'dorosak_lessons',
  'question-bank': 'question_bank',
  'malicious-example': 'malicious_example',
};

export function workflowName(keyOrId: string, t: T): string {
  const key = `wf.name.${BY_ID[keyOrId] ?? keyOrId}`;
  return has(key) ? t(key) : keyOrId;
}

export function sampleName(key: string, t: T): string {
  if (key.startsWith('upload:')) return t('sample.upload', { name: key.slice('upload:'.length) });
  const k = `sample.${key}`;
  return has(k) ? t(k) : key;
}

export function stationName(type: string, fallback: string, t: T): string {
  const k = `node.${type}.label`;
  return has(k) ? t(k) : fallback;
}

export function modeName(mode: string, t: T): string {
  const k = `mode.${mode}`;
  return has(k) ? t(k) : mode;
}

// a drafts file name -> the workflow it belongs to
export function draftsFileWorkflow(file: string): string {
  if (file === 'python_drafts.json') return 'dorosak_lessons';
  const m = file.match(/^python_(.+)_drafts\.json$/);
  return m ? (BY_ID[m[1]] ?? m[1]) : file;
}

// the title a person wrote, from the first step that has one. the id only if there is none.
export function itemTitle(item: { source_id: unknown; trace: { input: unknown }[] }): string {
  for (const e of item.trace) {
    const data = e.input as Record<string, unknown> | null;
    const title = data && typeof data === 'object' ? data.title ?? data.question : undefined;
    if (typeof title === 'string' && title.trim()) return title.trim();
  }
  return String(item.source_id);
}

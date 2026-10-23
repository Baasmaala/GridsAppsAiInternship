import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';

import { DEFAULT_WORKFLOW, ROOT } from '../engine/executor.mjs';

export { ROOT };
export const LESSON = { source_id: 'L1', title: 'Greetings', category: 'Conversations',
  level: 'A1', language: 'en', body: 'Hello! My name is Sara.' };
export const lesson = (changes = {}) => ({ ...LESSON, ...changes });

export const readJsonFile = file => JSON.parse(fs.readFileSync(file, 'utf8'));
export const baseWorkflow = () => readJsonFile(DEFAULT_WORKFLOW);
export const sample = name => readJsonFile(path.join(ROOT, 'masar', 'samples', name));

// build a straight-line workflow from node types, ids are n1, n2...
export function chain(types, extra = {}) {
  const nodes = types.map((t, i) => ({ id: `n${i + 1}`, type: t }));
  const edges = types.slice(1).map((_, i) => [`n${i + 1}`, `n${i + 2}`]);
  return { id: 'test', trigger: { type: 'manual' }, nodes, edges, ...extra };
}

export function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(value), 'utf8');
  return file;
}

export function folderHashes(folder) {
  if (!fs.existsSync(folder)) return null;
  const out = {};
  for (const name of fs.readdirSync(folder, { recursive: true }).sort()) {
    const file = path.join(folder, name);
    if (fs.statSync(file).isFile()) out[name] = createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  }
  return out;
}

// run_id, timestamps and ms change every run, the rest must not
export function withoutTimes(report) {
  const r = structuredClone(report);
  delete r.run_id;
  delete r.generated_at;
  for (const item of r.items) for (const entry of item.trace) delete entry.ms;
  return r;
}

// a fresh temp folder per test: dir/output/<store>
export function sandbox(fn, storeName = 'node_drafts.json') {
  return async () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'masar-'));
    const dir = path.join(tmp, 'output');
    try {
      await fn({ tmp, dir, store: path.join(dir, storeName),
        drafts: () => readJsonFile(path.join(dir, storeName)) });
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  };
}

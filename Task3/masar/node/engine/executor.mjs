import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { performance } from 'node:perf_hooks';
import { fileURLToPath } from 'node:url';

import { NODES } from './registry.mjs';
import { makeRun } from './context.mjs';
import { ValidationError } from './errors.mjs';
import { Workflow, loadWorkflow, parseWorkflow } from './loader.mjs';
import { isObject } from './nodes/lesson_nodes.mjs';
import { atomicJsonWrite, readStore } from './storage.mjs';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
export const DEFAULT_WORKFLOW = path.join(ROOT, 'masar', 'workflows', 'dorosak_lessons.json');

export function runWorkflow(lessons, { approvedBy = '', dryRun = false, store,
  workflowPath = DEFAULT_WORKFLOW, workflow } = {}) {
  if (!store) throw new Error('store path is required');
  let wf;
  if (workflow === undefined) wf = loadWorkflow(workflowPath);
  else if (workflow instanceof Workflow) wf = workflow;
  else wf = parseWorkflow(workflow);
  if (!Array.isArray(lessons)) throw new Error('Input must be a JSON array');

  const saved = readStore(store);
  // trim once here, so "   " counts as no reviewer everywhere
  const reviewer = typeof approvedBy === 'string' ? approvedBy.trim() : '';
  const now = new Date().toISOString();
  const run = makeRun({ reviewer, dryRun, allowedLanguages: wf.allowedLanguages, now,
    knownIds: saved.filter(d => isObject(d) && typeof d.source_id === 'string').map(d => d.source_id) });

  const items = lessons.map(raw => runItem(raw, wf.nodes, run));

  if (run.newDrafts.length && run.reviewer && !dryRun) atomicJsonWrite(store, [...saved, ...run.newDrafts]);

  const statuses = items.map(i => i.status);
  return {
    run_id: randomUUID(),
    workflow_id: wf.id,
    workflow_version: wf.version,
    generated_at: now,
    mode: dryRun ? 'dry-run' : (reviewer ? 'approved' : 'review'),
    summary: Object.fromEntries([...new Set(statuses)].sort()
      .map(s => [s, statuses.filter(x => x === s).length])),
    items,
  };
}

function runItem(raw, nodes, run) {
  let data = structuredClone(raw);
  let status = 'running';
  let error = null;
  const steps = [];
  const trace = [];
  for (const node of nodes) {
    steps.push(node.id);
    const entry = { node: node.id, type: node.type, input: structuredClone(data) };
    const start = performance.now();
    let result;
    try {
      result = NODES[node.type](data, run);
    } catch (ex) {
      if (ex instanceof ValidationError) {
        status = 'failed_validation';
        error = ex.message;
      } else {
        // a bug in a node, not bad input. this lesson stops, the others go on
        status = 'failed_error';
        error = ex instanceof Error ? `${ex.name}: ${ex.message}` : `Error: ${String(ex)}`;
      }
    }
    entry.ms = Math.round((performance.now() - start) * 1000) / 1000;
    if (error !== null) {
      Object.assign(entry, { result: 'error', status, error });
      trace.push(entry);
      break;
    }
    data = result.data;
    entry.output = structuredClone(data);
    entry.result = result.stop ? 'stop' : 'ok';
    if (result.status) status = entry.status = result.status;
    if (result.note) entry.note = result.note;
    trace.push(entry);
    if (result.stop) break;
  }
  if (status === 'running') status = 'complete';

  const item = { source_id: isObject(raw) && Object.hasOwn(raw, 'source_id') ? raw.source_id : 'UNKNOWN',
    status, steps };
  if (isObject(data) && Object.hasOwn(data, 'word_count')) item.word_count = data.word_count;
  if (error !== null) item.error = error;
  item.trace = trace;
  return item;
}

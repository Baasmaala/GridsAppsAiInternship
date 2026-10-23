/** Educational n8n-inspired sequential engine; NO Dorosak production access. */
import { readFile, writeFile, rename, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const WORKFLOW = path.join(ROOT, 'shared', 'workflow.json');
const INPUT = path.join(ROOT, 'shared', 'lessons.json');
const LEVELS = new Set(['A1', 'A2', 'B1', 'B2', 'C1', 'C2']);
const REQUIRED = ['source_id', 'title', 'category', 'level', 'language', 'body'];
const SUPPORTED = new Set(['validate_lesson', 'normalize_lesson', 'check_duplicate',
  'manual_approval', 'save_draft', 'log_result']);
const slugify = s => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

async function atomicJsonWrite(file, value) {
  await mkdir(path.dirname(file), { recursive: true });
  const tmp = `${file}.${randomUUID()}.tmp`;
  await writeFile(tmp, JSON.stringify(value, null, 2) + '\n', 'utf8');
  await rename(tmp, file);
}

export async function runWorkflow(lessons, { approvedBy = '', dryRun = false, store,
    workflowPath = WORKFLOW } = {}) {
  if (!store) throw new Error('store path is required');
  const wf = JSON.parse(await readFile(workflowPath, 'utf8'));
  const nodes = wf.nodes;
  const expected = nodes.slice(1).map((n, i) => [nodes[i].id, n.id]);
  if (JSON.stringify(wf.edges) !== JSON.stringify(expected)) {
    throw new Error('PoC only supports a sequential chain, not arbitrary DAGs');
  }
  if (nodes.some(n => !SUPPORTED.has(n.type))) throw new Error('Unknown node type');
  const saved = existsSync(store) ? JSON.parse(await readFile(store, 'utf8')) : [];
  if (!Array.isArray(saved)) throw new Error('Store must contain a JSON array');
  const known = new Set(saved.map(x => x.source_id));
  const outcomes = [];
  for (const raw of lessons) {
    const ctx = { data: { ...raw }, steps: [], status: 'running' };
    try {
      for (const node of nodes) {
        ctx.steps.push(node.id);
        let d = ctx.data;
        switch (node.type) {
          case 'validate_lesson': {
            const missing = REQUIRED.filter(k => typeof d[k] !== 'string' || !d[k].trim());
            if (missing.length) throw new Error(`Missing/empty field: ${missing.join(', ')}`);
            if (!LEVELS.has(d.level.trim().toUpperCase())) throw new Error('Invalid CEFR level');
            if (d.language.trim().toLowerCase() !== 'en') throw new Error('Only English lessons allowed');
            break;
          }
          case 'normalize_lesson': {
            d = Object.fromEntries(REQUIRED.map(k => [k, d[k].trim()]));
            d.level = d.level.toUpperCase();
            d.language = d.language.toLowerCase();
            d.slug = slugify(d.title);
            d.status = 'draft';
            if (!d.slug) throw new Error('Cannot generate slug');
            ctx.data = d;
            break;
          }
          case 'check_duplicate':
            if (known.has(d.source_id)) ctx.status = 'skipped_duplicate';
            break;
          case 'manual_approval':
            if (!approvedBy.trim()) ctx.status = 'review_pending';
            break;
          case 'save_draft':
            if (dryRun) ctx.status = 'dry_run_preview';
            else {
              saved.push({ ...d, reviewed_by: approvedBy.trim() });
              known.add(d.source_id);
              ctx.status = 'draft_saved';
            }
            break;
          case 'log_result':
            break;
        }
        if (ctx.status === 'review_pending' || ctx.status === 'skipped_duplicate') break;
      }
      if (ctx.status === 'running') ctx.status = 'complete';
    } catch (ex) {
      ctx.status = 'failed_validation';
      ctx.error = ex.message;
    }
    outcomes.push({ source_id: raw?.source_id ?? 'UNKNOWN', status: ctx.status,
      steps: ctx.steps, ...(ctx.error ? { error: ctx.error } : {}) });
  }
  // Single-process educational demo; no concurrent writer protection.
  if (!dryRun && approvedBy.trim()) await atomicJsonWrite(store, saved);
  return { run_id: randomUUID(), workflow_id: wf.id,
    generated_at: new Date().toISOString(),
    mode: dryRun ? 'dry-run' : approvedBy ? 'approved' : 'review',
    summary: Object.fromEntries([...new Set(outcomes.map(x => x.status))].sort()
      .map(s => [s, outcomes.filter(x => x.status === s).length])), items: outcomes };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const val = key => args.includes(key) ? args[args.indexOf(key) + 1] : undefined;
  const approvedBy = val('--approved-by') || '';
  const dryRun = args.includes('--dry-run');
  const input = val('--input') || INPUT;
  const store = val('--store') || path.join(ROOT, 'output', 'node_drafts.json');
  const lessons = JSON.parse(await readFile(input, 'utf8'));
  if (!Array.isArray(lessons)) throw new Error('Input must be a JSON array');
  console.log(JSON.stringify(await runWorkflow(lessons, { approvedBy, dryRun, store }), null, 2));
}

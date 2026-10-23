import fs from 'node:fs';
import path from 'node:path';
import { parseArgs } from 'node:util';

import { StoreError, WorkflowError } from './engine/errors.mjs';
import { DEFAULT_WORKFLOW, ROOT, runWorkflow } from './engine/executor.mjs';
import { renderHtml } from './engine/html_report.mjs';
import { loadWorkflow, readJson, toMermaid } from './engine/loader.mjs';

const OUTPUT_DIR = path.join(ROOT, 'output');
const DEFAULT_INPUT = path.join(ROOT, 'masar', 'samples', 'lessons_good.json');
const LESSONS_ID = 'dorosak-content-intake';

// the lessons workflow keeps the brief's file name, other workflows get their own file
function defaultStore(workflowId) {
  if (workflowId === LESSONS_ID) return path.join(OUTPUT_DIR, 'node_drafts.json');
  return path.join(OUTPUT_DIR, `node_${workflowId.replace(/[^A-Za-z0-9_-]/g, '_')}_drafts.json`);
}

const OPTIONS = {
  workflow: { type: 'string', default: DEFAULT_WORKFLOW },
  input: { type: 'string', default: DEFAULT_INPUT },
  store: { type: 'string' },
  'approved-by': { type: 'string', default: '' },
  'dry-run': { type: 'boolean', default: false },
  lint: { type: 'boolean', default: false },
  graph: { type: 'boolean', default: false },
  'report-html': { type: 'string' },
  trace: { type: 'boolean', default: false },
  help: { type: 'boolean', short: 'h', default: false },
};

const USAGE = `usage: node masar/node/cli.mjs [options]

Masar: Dorosak lesson intake, local sandbox only

  --workflow FILE      workflow file (default masar/workflows/dorosak_lessons.json)
  --input FILE         lessons file (default masar/samples/lessons_good.json)
  --store FILE         drafts file (default depends on the workflow)
  --approved-by NAME   test reviewer name, not a real login
  --dry-run            run everything, save nothing
  --lint               only check the workflow file
  --graph              print the workflow as a Mermaid diagram
  --report-html FILE   also save a readable report
  --trace              show the per-node trace in the output`;

function inside(file, folder) {
  const rel = path.relative(path.resolve(folder), path.resolve(file));
  return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));
}

function fail(msg, code = 2) {
  process.stderr.write(msg + '\n');
  return code;
}

function main(argv) {
  let args;
  try {
    args = parseArgs({ args: argv, options: OPTIONS, strict: true, allowPositionals: false }).values;
  } catch (ex) {
    return fail(`${USAGE}\n\nmasar: ${ex.message}`);
  }
  if (args.help) {
    process.stdout.write(USAGE + '\n');
    return 0;
  }

  let wf;
  try {
    wf = loadWorkflow(args.workflow);
  } catch (ex) {
    if (!(ex instanceof WorkflowError)) throw ex;
    return fail([`workflow rejected: ${args.workflow}`, ...ex.errors.map(e => `  - ${e}`)].join('\n'), 1);
  }
  if (args.lint) {
    process.stdout.write(`workflow ok: ${wf.id} (${wf.nodes.length} nodes, one straight line)\n`);
    return 0;
  }
  if (args.graph) {
    process.stdout.write(toMermaid(wf) + '\n');
    return 0;
  }

  const store = args.store ?? defaultStore(wf.id);
  const html = args['report-html'];
  if (args['dry-run'] && html && (inside(html, OUTPUT_DIR) || inside(html, path.dirname(store)))) {
    return fail('dry run never writes in the output folder. pick another path for --report-html');
  }

  let lessons;
  try {
    lessons = readJson(args.input);
  } catch (ex) {
    return fail(`cannot read input ${args.input}: ${ex.message}`);
  }
  if (!Array.isArray(lessons)) return fail('Input must be a JSON array');

  let report;
  try {
    report = runWorkflow(lessons, { approvedBy: args['approved-by'], dryRun: args['dry-run'],
      store, workflow: wf });
  } catch (ex) {
    if (ex instanceof StoreError) return fail(ex.message);
    throw ex;
  }

  if (html) {
    fs.mkdirSync(path.dirname(path.resolve(html)), { recursive: true });
    fs.writeFileSync(html, renderHtml(report), 'utf8');
  }

  if (!args.trace) {
    report = { ...report, items: report.items.map(({ trace, ...rest }) => rest) };
  }
  process.stdout.write(JSON.stringify(report, null, 2) + '\n');
  return 0;
}

process.exitCode = main(process.argv.slice(2));

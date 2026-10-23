import { test } from 'node:test';
import assert from 'node:assert/strict';

import { WorkflowError } from '../engine/errors.mjs';
import { DEFAULT_WORKFLOW } from '../engine/executor.mjs';
import { lint } from '../engine/lint.mjs';
import { loadWorkflow, parseWorkflow, toMermaid } from '../engine/loader.mjs';
import { baseWorkflow, chain } from './helpers.mjs';

const FULL = ['validate_lesson', 'normalize_lesson', 'word_count', 'check_duplicate',
  'manual_approval', 'save_draft', 'log_result'];

function assertRejected(wf, text) {
  const errors = lint(wf);
  assert.ok(errors.some(e => e.includes(text)), `${JSON.stringify(text)} not in ${JSON.stringify(errors)}`);
}

test('default workflow is ok', () => {
  assert.deepEqual(lint(baseWorkflow()), []);
  const wf = loadWorkflow(DEFAULT_WORKFLOW);
  assert.deepEqual(wf.allowedLanguages, ['en']);
  assert.deepEqual(wf.nodes.map(n => n.type), FULL);
});

test('unknown node type', () => {
  assertRejected(chain(['validate_lesson', 'exec_python']), "unknown node type 'exec_python'");
});

test('code field on node', () => {
  const wf = chain(FULL);
  wf.nodes[0].code = "require('fs').rmSync('x')";
  assertRejected(wf, "key 'code' is not allowed. workflow.json is a description, not code");
});

test('code field on workflow', () => {
  assertRejected(chain(FULL, { script: 'rm -rf /' }), "key 'script' is not allowed");
});

test('unknown key', () => {
  const wf = chain(FULL);
  wf.nodes[1].color = 'red';
  assertRejected(wf, "unknown key 'color'");
});

test('cycle', () => {
  let wf = chain(FULL);
  wf.edges.push(['n7', 'n1']);
  assertRejected(wf, 'cycle found: n1 -> n2');
  wf = chain(['validate_lesson', 'normalize_lesson', 'log_result']);
  wf.edges = [['n1', 'n2'], ['n2', 'n3'], ['n3', 'n2']];
  assertRejected(wf, 'more than one node before it');
  wf.edges = [['n2', 'n3'], ['n3', 'n2']];
  assertRejected(wf, 'cycle found: n2 -> n3 -> n2');
  wf.edges = [['n1', 'n1']];
  assertRejected(wf, 'cycle found: n1 -> n1');
});

test('missing edge target', () => {
  const wf = chain(FULL);
  wf.edges[wf.edges.length - 1] = ['n6', 'ghost'];
  assertRejected(wf, "points to a missing node 'ghost'");
});

test('duplicate node id', () => {
  const wf = chain(FULL);
  wf.nodes[1].id = 'n1';
  assertRejected(wf, "node 'n1': duplicate node id");
});

test('branch is not linear', () => {
  const wf = chain(FULL);
  wf.edges.push(['n1', 'n3']);
  assertRejected(wf, "n1' has more than one next node");
});

test('separate parts', () => {
  const wf = chain(FULL);
  wf.edges.splice(2, 1);
  assertRejected(wf, '2 separate parts');
});

test('bad edge shape', () => {
  const wf = chain(FULL);
  wf.edges[0] = 'n1->n2';
  assertRejected(wf, 'edge 1: must be a [from, to] pair');
});

test('save needs approval before it', () => {
  assertRejected(chain(['validate_lesson', 'normalize_lesson', 'check_duplicate', 'save_draft']),
    'no human approval, no save');
  // approval after save does not count
  assertRejected(chain(['validate_lesson', 'normalize_lesson', 'check_duplicate', 'save_draft', 'manual_approval']),
    'no human approval, no save');
});

test('save needs duplicate check', () => {
  assertRejected(chain(['validate_lesson', 'normalize_lesson', 'manual_approval', 'save_draft']),
    'save_draft needs a check_duplicate node before it');
});

test('trigger must be manual', () => {
  const wf = chain(FULL);
  wf.trigger = { type: 'webhook' };
  assertRejected(wf, "trigger: type must be 'manual'");
});

test('allowed_languages shape', () => {
  for (const bad of [[], 'en', [''], [1]]) assertRejected(chain(FULL, { allowed_languages: bad }), 'allowed_languages');
});

test('edges order wins over nodes order', () => {
  const wf = chain(FULL);
  wf.nodes.reverse();
  assert.deepEqual(parseWorkflow(wf).nodes.map(n => n.type), FULL);
});

test('parse throws with all errors', () => {
  const wf = chain(['validate_lesson', 'exec_python']);
  wf.nodes[0].eval = '1';
  assert.throws(() => parseWorkflow(wf), err => err instanceof WorkflowError && err.errors.length === 2);
});

test('"__proto__" or "constructor" is not a node type', () => {
  for (const type of ['__proto__', 'constructor', 'toString']) {
    assertRejected(chain(['validate_lesson', type]), 'unknown node type');
  }
});

test('mermaid', () => {
  const text = toMermaid(loadWorkflow(DEFAULT_WORKFLOW));
  assert.ok(text.startsWith('flowchart LR'));
  assert.ok(text.includes('n5["approval<br/>manual_approval"]'));
  assert.ok(text.includes('n6 --> n7'));
});

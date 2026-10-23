import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { describe, mock, test } from 'node:test';
import assert from 'node:assert/strict';

import { NODES } from '../engine/registry.mjs';
import { WorkflowError } from '../engine/errors.mjs';
import { runWorkflow } from '../engine/executor.mjs';
import { cleanForCompare, fingerprint } from '../engine/fingerprint.mjs';
import { lint } from '../engine/lint.mjs';
import { ROOT, baseWorkflow, chain, lesson, readJsonFile, sample, sandbox, writeJson } from './helpers.mjs';

const QUESTION_WF = path.join(ROOT, 'masar', 'workflows', 'question_bank.json');
const EVIL = path.join(ROOT, 'masar', 'workflows', 'malicious_example.json');
const QUESTIONS = sample('questions.json');

function enAr() {
  const wf = baseWorkflow();
  wf.allowed_languages = ['en', 'ar'];
  return wf;
}

describe('fingerprint', () => {
  test('english', () => {
    assert.equal(cleanForCompare('  Greetings, and  INTRODUCTIONS! '), 'greetings and introductions');
    assert.equal(cleanForCompare('Ask-for: directions?'), 'ask for directions');
  });

  test('arabic', () => {
    assert.equal(cleanForCompare('التَّحِيّـات'), 'التحيات');
    assert.equal(cleanForCompare('أحمد إلى آدم ٱلبيت'), 'احمد الي ادم البيت');
    assert.equal(cleanForCompare('مكتبة'), 'مكتبه');
  });

  test('same print for same title, none for no letters', () => {
    assert.equal(fingerprint('مكتبة المدرسة'), fingerprint('مكتبه  المدرسه'));
    assert.notEqual(fingerprint('Greetings'), fingerprint('Greeting'));
    for (const text of ['', '   ', '!!!', null, 5]) assert.equal(fingerprint(text), null);
  });

  test('similar sample', sandbox(({ store }) => {
    const r = runWorkflow(sample('lessons_similar.json'), { store, approvedBy: 'Trainer', dryRun: true, workflow: enAr() });
    assert.deepEqual(r.items.map(i => [i.source_id, i.status, i.possible_duplicate_of ?? null]), [
      ['DOR-SIM-001', 'dry_run_preview', null],
      ['DOR-SIM-002', 'possible_duplicate', 'DOR-SIM-001'],
      ['DOR-SIM-003', 'dry_run_preview', null],
      ['DOR-SIM-004', 'possible_duplicate', 'DOR-SIM-003'],
      ['DOR-SIM-005', 'dry_run_preview', null],
      ['DOR-SIM-006', 'possible_duplicate', 'DOR-SIM-005'],
      ['DOR-SIM-007', 'dry_run_preview', null],
      ['DOR-SIM-008', 'possible_duplicate', 'DOR-SIM-007'],
      ['DOR-SIM-009', 'dry_run_preview', null],
    ]);
  }));

  test('approved run does not save a possible duplicate', sandbox(({ store, drafts }) => {
    runWorkflow([lesson({ source_id: 'OLD', title: 'Greetings' })], { store, approvedBy: 'Trainer' });
    const r = runWorkflow([lesson({ source_id: 'NEW', title: 'GREETINGS!' })], { store, approvedBy: 'Trainer' });
    assert.equal(r.items[0].status, 'possible_duplicate');
    assert.equal(r.items[0].possible_duplicate_of, 'OLD');
    assert.deepEqual(drafts().map(d => d.source_id), ['OLD']);
  }));

  test('stored text is not changed', sandbox(({ store, drafts }) => {
    runWorkflow([lesson({ title: 'التَّحِيّات', language: 'ar' })], { store, approvedBy: 'Trainer', workflow: enAr() });
    assert.equal(drafts()[0].title, 'التَّحِيّات');
    assert.equal(drafts()[0].title_fingerprint, fingerprint('التحيات'));
  }));

  test('old drafts without fingerprint still match', sandbox(({ store }) => {
    writeJson(store, [{ source_id: 'OLD', title: 'Greetings', status: 'draft' }]);
    const r = runWorkflow([lesson({ source_id: 'NEW', title: 'greetings' })], { store, dryRun: true });
    assert.equal(r.items[0].possible_duplicate_of, 'OLD');
  }));

  test('python and node make the same fingerprint', () => {
    // fingerprints.json was made by the python engine
    const fromPython = readJsonFile(path.join(ROOT, 'masar', 'node', 'tests', 'fingerprints.json'));
    for (const [text, fp] of Object.entries(fromPython)) assert.equal(fingerprint(text), fp, text);
  });
});

describe('question bank', () => {
  const runQ = (items, opts) => runWorkflow(items, { workflowPath: QUESTION_WF, ...opts });

  test('sample', sandbox(({ store }) => {
    const r = runQ(QUESTIONS, { store, approvedBy: 'Trainer' });
    assert.deepEqual(r.items.map(i => [i.source_id, i.status, i.error ?? '']), [
      ['TC-Q-001', 'draft_saved', ''],
      ['TC-Q-002', 'draft_saved', ''],
      ['TC-Q-003', 'failed_validation', 'options must be a list of exactly 4 answers (got 3)'],
      ['TC-Q-004', 'failed_validation', 'options repeat: red'],
      ['TC-Q-005', 'failed_validation', 'answer must be the number of the right option, 0 to 3 (got 4)'],
      ['TC-Q-006', 'failed_validation', 'answer must be the number of the right option, 0 to 3 (got True)'],
      ['TC-Q-007', 'failed_validation', 'option 2 is empty'],
      ['TC-Q-008', 'failed_validation', 'Missing/empty field: topic'],
      ['TC-Q-009', 'possible_duplicate', ''],
      ['TC-Q-001', 'skipped_duplicate', ''],
    ]);
  }));

  test('normalize keeps only known fields', sandbox(({ store, drafts }) => {
    runQ([{ ...QUESTIONS[0], source_id: 'X', status: 'published', secret: 'no' }], { store, approvedBy: 'Trainer' });
    runQ([QUESTIONS[1]], { store, approvedBy: 'Trainer' });
    const [a, b] = drafts();
    assert.equal('secret' in a, false);
    assert.equal(a.status, 'draft');
    assert.deepEqual([b.question, b.options[0], b.level, b.topic],
      ["What is the past of 'buy'?", 'bought', 'A2', 'Irregular verbs']);
  }));

  test('save needs a validator', () => {
    const errors = lint(chain(['check_duplicate', 'manual_approval', 'save_draft']));
    assert.ok(errors.includes('save_draft needs a validate node before it (nothing unchecked is saved)'));
    assert.ok(errors.includes('check_duplicate needs a validate node before it'));
  });
});

describe('malicious workflow', () => {
  test('lint names every problem', () => {
    const errors = lint(readJsonFile(EVIL));
    assert.ok(errors.includes("workflow: key 'script' is not allowed. workflow.json is a description, not code"));
    assert.ok(errors.includes("node 'sneak': key 'code' is not allowed. workflow.json is a description, not code"));
    assert.ok(errors.some(e => e.includes("node 'sneak': unknown node type 'exec_python'")));
  });

  test('no node runs at all', sandbox(({ store, dir }) => {
    const spies = Object.keys(NODES).map(name => mock.method(NODES, name));
    try {
      assert.throws(() => runWorkflow([lesson()], { store, approvedBy: 'Trainer', workflowPath: EVIL }), WorkflowError);
      for (const spy of spies) assert.equal(spy.mock.callCount(), 0);
    } finally {
      for (const spy of spies) spy.mock.restore();
    }
    assert.equal(fs.existsSync(dir), false);
  }));

  test('cli refuses it', sandbox(({ store, dir }) => {
    const r = spawnSync(process.execPath, [path.join(ROOT, 'masar', 'node', 'cli.mjs'), '--workflow', EVIL,
      '--approved-by', 'Trainer', '--store', store], { encoding: 'utf8' });
    assert.equal(r.status, 1);
    assert.match(r.stderr, /exec_python/);
    assert.equal(fs.existsSync(dir), false);
  }));
});

import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { ROOT, baseWorkflow, chain, lesson, sandbox, writeJson } from './helpers.mjs';

const CLI = path.join(ROOT, 'masar', 'node', 'cli.mjs');
const masar = (...args) => spawnSync(process.execPath, [CLI, ...args], { cwd: ROOT, encoding: 'utf8' });

test('lint ok', () => {
  const r = masar('--lint');
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /workflow ok: dorosak-content-intake/);
});

test('lint refuses code', sandbox(({ tmp }) => {
  const wf = chain(['validate_lesson', 'exec_python']);
  wf.nodes[0].code = 'console.log(1)';
  const r = masar('--lint', '--workflow', writeJson(path.join(tmp, 'evil.json'), wf));
  assert.equal(r.status, 1);
  assert.match(r.stderr, /workflow rejected/);
  assert.match(r.stderr, /not code/);
  assert.match(r.stderr, /exec_python/);
}));

test('bad workflow stops a run', sandbox(({ tmp, store, dir }) => {
  const r = masar('--workflow', writeJson(path.join(tmp, 'evil.json'), { id: 'x' }),
    '--approved-by', 'Trainer', '--store', store);
  assert.equal(r.status, 1);
  assert.equal(fs.existsSync(dir), false);
}));

test('graph', () => {
  const r = masar('--graph');
  assert.equal(r.status, 0);
  assert.ok(r.stdout.startsWith('flowchart LR'));
});

test('brief commands', sandbox(({ store }) => {
  const steps = [[['--dry-run', '--approved-by', 'Trainer'], 'dry_run_preview', 'dry-run'],
    [[], 'review_pending', 'review'],
    [['--approved-by', 'Trainer'], 'draft_saved', 'approved'],
    [['--approved-by', 'Trainer'], 'skipped_duplicate', 'approved']];
  for (const [args, status, mode] of steps) {
    const r = masar(...args, '--store', store);
    assert.equal(r.status, 0, r.stderr);
    const report = JSON.parse(r.stdout);
    assert.equal(report.mode, mode);
    assert.deepEqual(report.summary, { [status]: 4 });
    assert.equal('trace' in report.items[0], false);
    assert.equal(fs.existsSync(store), ['draft_saved', 'skipped_duplicate'].includes(status));
  }
}));

test('trace flag', sandbox(({ store }) => {
  const r = masar('--dry-run', '--approved-by', 'Trainer', '--trace', '--store', store);
  assert.equal(JSON.parse(r.stdout).items[0].trace.length, 7);
}));

test('dry run refuses html in output', sandbox(({ store, dir }) => {
  const r = masar('--dry-run', '--approved-by', 'Trainer', '--store', store,
    '--report-html', path.join(dir, 'report.html'));
  assert.equal(r.status, 2);
  assert.match(r.stderr, /dry run never writes in the output folder/);
  assert.equal(fs.existsSync(dir), false);
}));

test('html report', sandbox(({ tmp, store }) => {
  const html = path.join(tmp, 'report.html');
  const r = masar('--approved-by', 'Trainer', '--store', store, '--report-html', html);
  assert.equal(r.status, 0, r.stderr);
  const text = fs.readFileSync(html, 'utf8');
  assert.ok(text.includes('Masar run report'));
  assert.ok(text.includes('Drafts only. Nothing here is published.'));
  assert.ok(text.includes('DOR-CAT-004'));
}));

test('arabic output prints', sandbox(({ tmp, store }) => {
  const wf = baseWorkflow();
  wf.allowed_languages = ['ar'];
  const r = masar('--workflow', writeJson(path.join(tmp, 'wf.json'), wf),
    '--input', writeJson(path.join(tmp, 'in.json'), [lesson({ title: 'التحيات', language: 'ar', body: 'مرحبا كيف حالك' })]),
    '--store', store, '--approved-by', 'Trainer');
  assert.equal(r.status, 0, r.stderr);
  assert.equal(JSON.parse(r.stdout).items[0].status, 'draft_saved');
}));

test('input with BOM', sandbox(({ tmp, store }) => {
  const file = path.join(tmp, 'bom.json');
  fs.writeFileSync(file, '﻿' + JSON.stringify([lesson()]), 'utf8');
  assert.equal(masar('--input', file, '--store', store).status, 0);
}));

test('input not a list', sandbox(({ tmp, store }) => {
  const r = masar('--input', writeJson(path.join(tmp, 'in.json'), lesson()), '--store', store);
  assert.equal(r.status, 2);
  assert.match(r.stderr, /Input must be a JSON array/);
}));

test('unknown flag is refused', () => {
  const r = masar('--publish');
  assert.equal(r.status, 2);
  assert.match(r.stderr, /usage:/);
});

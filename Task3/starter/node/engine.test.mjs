import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { runWorkflow } from './engine.mjs';

const lesson = {source_id: 'L1', title: 'Greetings', category: 'Conversations',
  level: 'A1', language: 'en', body: 'Hello!'};
async function sandbox(fn) {
  const d = await mkdtemp(path.join(tmpdir(), 'flow-lab-'));
  try { await fn(path.join(d, 'store.json')); } finally { await rm(d, {recursive: true, force: true}); }
}
test('approval required before saving', () => sandbox(async store => {
  const r = await runWorkflow([lesson], { store });
  assert.equal(r.items[0].status, 'review_pending');
}));
test('duplicate is skipped and only draft is saved', () => sandbox(async store => {
  assert.equal((await runWorkflow([lesson], {store, approvedBy: 'Trainer'})).items[0].status, 'draft_saved');
  assert.equal((await runWorkflow([lesson], {store, approvedBy: 'Trainer'})).items[0].status, 'skipped_duplicate');
  assert.equal(JSON.parse(await readFile(store, 'utf8'))[0].status, 'draft');
}));
test('invalid rejected', () => sandbox(async store => {
  const r = await runWorkflow([{...lesson, title: ''}], {store, approvedBy: 'Trainer'});
  assert.equal(r.items[0].status, 'failed_validation');
}));
test('dry run previews', () => sandbox(async store => {
  const r = await runWorkflow([lesson], {store, approvedBy: 'Trainer', dryRun: true});
  assert.equal(r.items[0].status, 'dry_run_preview');
}));

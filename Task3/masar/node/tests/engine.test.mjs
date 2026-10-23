import fs from 'node:fs';
import { describe, mock, test } from 'node:test';
import assert from 'node:assert/strict';

import { NODES } from '../engine/registry.mjs';
import { StoreError, WorkflowError } from '../engine/errors.mjs';
import { runWorkflow } from '../engine/executor.mjs';
import { baseWorkflow, chain, folderHashes, lesson, sample, sandbox, withoutTimes, writeJson } from './helpers.mjs';

const GOOD = sample('lessons_good.json');
const BAD = sample('lessons_bad.json');

// the 5 challenges from page 5 of the brief
describe('brief challenges', () => {
  test('1 empty title fails and saves nothing', sandbox(({ store }) => {
    const r = runWorkflow([lesson({ title: '' })], { store, approvedBy: 'Trainer' });
    assert.equal(r.items[0].status, 'failed_validation');
    assert.match(r.items[0].error, /title/);
    assert.equal(fs.existsSync(store), false);
  }));

  test('2 approved twice is skipped_duplicate', sandbox(({ store, drafts }) => {
    const first = runWorkflow([lesson()], { store, approvedBy: 'Trainer' });
    const second = runWorkflow([lesson()], { store, approvedBy: 'Trainer' });
    assert.equal(first.items[0].status, 'draft_saved');
    assert.equal(second.items[0].status, 'skipped_duplicate');
    assert.equal(drafts().length, 1);
  }));

  test('3 no reviewer is review_pending', sandbox(({ store, dir }) => {
    const r = runWorkflow([lesson()], { store });
    assert.equal(r.items[0].status, 'review_pending');
    assert.equal(r.mode, 'review');
    assert.equal(fs.existsSync(dir), false);
  }));

  test('4 dry run changes nothing in output', sandbox(({ store, dir }) => {
    runWorkflow(GOOD.slice(0, 2), { store, approvedBy: 'Trainer' });
    const before = folderHashes(dir);
    const r = runWorkflow(GOOD, { store, approvedBy: 'Trainer', dryRun: true });
    assert.deepEqual(folderHashes(dir), before);
    assert.deepEqual(r.summary, { dry_run_preview: 2, skipped_duplicate: 2 });
  }));

  test('4 dry run does not create output', sandbox(({ store, dir }) => {
    runWorkflow(GOOD, { store, approvedBy: 'Trainer', dryRun: true });
    assert.equal(fs.existsSync(dir), false);
  }));

  test('5 word_count in draft and report', sandbox(({ store, drafts }) => {
    const r = runWorkflow([lesson({ body: 'Hello! My name is Sara.' })], { store, approvedBy: 'Trainer' });
    assert.equal(r.items[0].word_count, 5);
    assert.equal(drafts()[0].word_count, 5);
  }));
});

// the AI review prompt on page 5, plus the hard rules
describe('review prompt rules', () => {
  test('every saved record is draft', sandbox(({ store, drafts }) => {
    runWorkflow([...GOOD, lesson({ source_id: 'L9', status: 'published' })], { store, approvedBy: 'Trainer' });
    assert.equal(drafts().length, 5);
    for (const d of drafts()) {
      assert.equal(d.status, 'draft');
      assert.equal(d.reviewed_by, 'Trainer');
      assert.ok(d.saved_at);
    }
  }));

  test('level 9A rejected and " b1 " cleaned', sandbox(({ store, drafts }) => {
    const r = runWorkflow([lesson({ source_id: 'A', level: '9A' }), lesson({ source_id: 'B', level: ' b1 ' })],
      { store, approvedBy: 'Trainer' });
    assert.equal(r.items[0].status, 'failed_validation');
    assert.match(r.items[0].error, /Invalid CEFR level/);
    assert.equal(r.items[1].status, 'draft_saved');
    assert.equal(drafts()[0].level, 'B1');
  }));

  test('all missing fields listed at once', sandbox(({ store }) => {
    const r = runWorkflow([{ source_id: 'X', level: 'A1', language: 'en' }], { store });
    assert.equal(r.items[0].error, 'Missing/empty field: title, category, body');
  }));

  test('same dry run twice gives same report', sandbox(({ store }) => {
    const a = runWorkflow([...GOOD, ...BAD], { store, approvedBy: 'Trainer', dryRun: true });
    const b = runWorkflow([...GOOD, ...BAD], { store, approvedBy: 'Trainer', dryRun: true });
    assert.deepEqual(withoutTimes(a), withoutTimes(b));
  }));

  test('language comes from the workflow setting', sandbox(({ store, drafts }) => {
    const arabic = lesson({ source_id: 'AR1', title: 'التحيات', language: 'ar', body: 'مرحبا كيف حالك' });
    let r = runWorkflow([arabic], { store, approvedBy: 'Trainer' });
    assert.equal(r.items[0].status, 'failed_validation');
    assert.match(r.items[0].error, /not allowed/);

    const wf = baseWorkflow();
    wf.allowed_languages = ['en', 'ar'];
    r = runWorkflow([arabic], { store, approvedBy: 'Trainer', workflow: wf });
    assert.equal(r.items[0].status, 'draft_saved');
    assert.equal(r.items[0].word_count, 3);
    assert.equal(drafts()[0].slug, 'التحيات');
  }));

  test('no workflow can skip approval', sandbox(({ store, dir }) => {
    const wf = chain(['validate_lesson', 'normalize_lesson', 'check_duplicate', 'save_draft']);
    assert.throws(() => runWorkflow([lesson()], { store, approvedBy: 'Trainer', workflow: wf }),
      err => err instanceof WorkflowError && /manual_approval/.test(err.message));
    assert.equal(fs.existsSync(dir), false);
  }));
});

describe('engine behaviour', () => {
  test('good sample saves all', sandbox(({ store }) => {
    assert.deepEqual(runWorkflow(GOOD, { store, approvedBy: 'Trainer' }).summary, { draft_saved: 4 });
  }));

  test('bad sample statuses', sandbox(({ store }) => {
    const r = runWorkflow(BAD, { store, approvedBy: 'Trainer' });
    assert.deepEqual(r.items.map(i => i.status), [
      'failed_validation', 'failed_validation', 'failed_validation', 'failed_validation',
      'failed_validation', 'draft_saved', 'skipped_duplicate', 'failed_validation']);
  }));

  test('normalize cleans but keeps meaning', sandbox(({ store, drafts }) => {
    runWorkflow([GOOD[3]], { store, approvedBy: 'Trainer' });
    const d = drafts()[0];
    assert.equal(d.title, 'Ordering Food');
    assert.equal(d.category, '75 Daily Conversations');
    assert.equal(d.language, 'en');
    assert.equal(d.body, 'I would like a cup of tea, please.');
    assert.deepEqual(d.tags, ['food', 'cafe']);
    assert.equal(d.slug, 'ordering-food');
  }));

  test('same id twice in one input, every mode', sandbox(({ store, drafts }) => {
    for (const opts of [{}, { dryRun: true, approvedBy: 'Trainer' }, { approvedBy: 'Trainer' }]) {
      const r = runWorkflow([lesson(), lesson()], { store, ...opts });
      assert.equal(r.items[1].status, 'skipped_duplicate');
      assert.equal(r.items[1].trace.at(-1).note, 'source_id came earlier in this input');
    }
    assert.equal(drafts().length, 1);
  }));

  test('trace has every node', sandbox(({ store }) => {
    const r = runWorkflow([lesson({ title: '  Greetings  ' })], { store, approvedBy: 'Trainer' });
    const trace = r.items[0].trace;
    assert.deepEqual(trace.map(t => t.node), r.items[0].steps);
    assert.equal(trace.length, 7);
    for (const t of trace) {
      assert.ok('input' in t && 'output' in t);
      assert.equal(typeof t.ms, 'number');
      assert.equal(t.result, 'ok');
    }
    assert.equal(trace[1].input.title, '  Greetings  ');
    assert.equal(trace[1].output.title, 'Greetings');
  }));

  test('trace shows where it stopped', sandbox(({ store }) => {
    const last = runWorkflow([lesson()], { store }).items[0].trace.at(-1);
    assert.deepEqual([last.node, last.result, last.status], ['approval', 'stop', 'review_pending']);
  }));

  test('bug in a node is failed_error', sandbox(({ store, drafts }) => {
    NODES.boom = (data, run) => {
      if (data.source_id === 'L2') throw new RangeError('something broke');
      return NODES.log_result(data, run);
    };
    try {
      const wf = baseWorkflow();
      wf.nodes.splice(2, 0, { id: 'boom', type: 'boom' });
      wf.edges = wf.nodes.slice(1).map((n, i) => [wf.nodes[i].id, n.id]);
      const r = runWorkflow(['L1', 'L2', 'L3'].map(s => lesson({ source_id: s, title: `Lesson ${s}` })),
        { store, approvedBy: 'Trainer', workflow: wf });
      assert.deepEqual(r.items.map(i => i.status), ['draft_saved', 'failed_error', 'draft_saved']);
      assert.equal(r.items[1].error, 'RangeError: something broke');
      assert.equal(drafts().length, 2);
    } finally {
      delete NODES.boom;
    }
  }));

  test('no temp file left after save', sandbox(({ store, dir }) => {
    runWorkflow([lesson()], { store, approvedBy: 'Trainer' });
    assert.deepEqual(fs.readdirSync(dir), ['node_drafts.json']);
  }));

  test('failed write keeps old file', sandbox(({ store, dir }) => {
    runWorkflow([lesson()], { store, approvedBy: 'Trainer' });
    const before = folderHashes(dir);
    const rename = mock.method(fs, 'renameSync', () => { throw new Error('disk full'); });
    try {
      assert.throws(() => runWorkflow([lesson({ source_id: 'L2', title: 'Other' })], { store, approvedBy: 'Trainer' }), /disk full/);
    } finally {
      rename.mock.restore();
    }
    assert.deepEqual(folderHashes(dir), before);
  }));

  test('file not rewritten when nothing new', sandbox(({ store }) => {
    runWorkflow([lesson()], { store, approvedBy: 'Trainer' });
    const mtime = fs.statSync(store).mtimeMs;
    const rename = mock.method(fs, 'renameSync');
    try {
      runWorkflow([lesson()], { store, approvedBy: 'Trainer' });
      assert.equal(rename.mock.callCount(), 0);
    } finally {
      rename.mock.restore();
    }
    assert.equal(fs.statSync(store).mtimeMs, mtime);
  }));

  test('broken store is refused', sandbox(({ store }) => {
    writeJson(store, { not: 'a list' });
    assert.throws(() => runWorkflow([lesson()], { store, approvedBy: 'Trainer' }), StoreError);
  }));

  test('keeps drafts already saved', sandbox(({ store, drafts }) => {
    runWorkflow([lesson({ source_id: 'OLD', title: 'Old one' })], { store, approvedBy: 'Ali' });
    runWorkflow([lesson({ source_id: 'NEW', title: 'New one' })], { store, approvedBy: 'Mona' });
    assert.deepEqual(drafts().map(d => [d.source_id, d.reviewed_by]), [['OLD', 'Ali'], ['NEW', 'Mona']]);
  }));
});

test('store path is required', () => {
  assert.throws(() => runWorkflow([lesson()], {}), /store path is required/);
});

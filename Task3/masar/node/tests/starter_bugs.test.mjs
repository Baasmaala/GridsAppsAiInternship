import fs from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { WorkflowError } from '../engine/errors.mjs';
import { runWorkflow } from '../engine/executor.mjs';
import { chain, lesson, sandbox } from './helpers.mjs';

// the 3 bugs from docs/NOTES.md "Bugs I found in the starter"

test('1 spaces-only reviewer is no reviewer', sandbox(({ store }) => {
  for (const name of ['   ', '\t', '']) {
    const r = runWorkflow([lesson()], { store, approvedBy: name });
    assert.equal(r.items[0].status, 'review_pending');
    assert.equal(r.mode, 'review');
    assert.equal(fs.existsSync(store), false);
  }
}));

test('1 reviewer name is trimmed', sandbox(({ store, drafts }) => {
  runWorkflow([lesson()], { store, approvedBy: '  Trainer ' });
  assert.equal(drafts()[0].reviewed_by, 'Trainer');
}));

test('2 normalize before validate is refused', sandbox(({ store }) => {
  const wf = chain(['normalize_lesson', 'validate_lesson', 'check_duplicate', 'manual_approval', 'save_draft']);
  assert.throws(() => runWorkflow([lesson()], { store, approvedBy: 'Trainer', workflow: wf }),
    err => err instanceof WorkflowError &&
      err.message.includes('normalize_lesson needs a validate_lesson node before it'));
}));

test('3 non-object lessons do not stop the run', sandbox(({ store }) => {
  const r = runWorkflow(['hello', 5, null, [1], lesson()], { store, approvedBy: 'Trainer' });
  assert.deepEqual(r.items.map(i => i.status), [...Array(4).fill('failed_validation'), 'draft_saved']);
  assert.equal(r.items[0].error, 'Lesson must be an object');
  assert.equal(r.items[0].source_id, 'UNKNOWN');
}));

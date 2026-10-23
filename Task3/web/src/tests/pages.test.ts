import { describe, expect, test } from 'vitest';

import type { Item, ReviewItem, RunSummary, WorkflowNode } from '../api/client';
import { en } from '../i18n/strings';
import { overviewCounts } from '../lib/counts';
import { diffFields } from '../lib/diff';
import { draftsFileWorkflow, sampleName, workflowName } from '../lib/names';
import { canApprove, canReject } from '../lib/review';
import { link, parseHash } from '../lib/route';
import { arrived, ticksNeeded, trainStop } from '../lib/train';

const t = (key: keyof typeof en, vars: Record<string, string | number> = {}) =>
  en[key].replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? `{${k}}`));

describe('review form rules', () => {
  test('approve needs a real name', () => {
    for (const name of ['', '   ', '\t', '\n ']) expect(canApprove(name), JSON.stringify(name)).toBe(false);
    expect(canApprove('Mona')).toBe(true);
    expect(canApprove('  Mona ')).toBe(true);
  });

  test('reject needs a name and a reason', () => {
    expect(canReject('Mona', '')).toBe(false);
    expect(canReject('Mona', '   ')).toBe(false);
    expect(canReject('   ', 'too long')).toBe(false);
    expect(canReject('Mona', 'too long')).toBe(true);
  });
});

describe('before and after', () => {
  test('finds added, changed, removed and same', () => {
    const rows = diffFields({ title: '  A  ', level: 'b1', keep: 1, gone: true }, { title: 'A', level: 'B1', keep: 1, slug: 'a' })!;
    expect(rows.map(r => [r.key, r.change])).toEqual([
      ['title', 'changed'], ['level', 'changed'], ['keep', 'same'], ['gone', 'removed'], ['slug', 'added']]);
  });

  test('no after (a failed step) shows every field as removed', () => {
    expect(diffFields({ a: 1 }, undefined)!.map(r => r.change)).toEqual(['removed']);
  });

  test('something that is not an object cannot be split into fields', () => {
    expect(diffFields('hello', 'hello')).toBeNull();
    expect(diffFields([1], { a: 1 })).toBeNull();
  });
});

describe('overview counts', () => {
  const run = (summary: Record<string, number>): RunSummary =>
    ({ run_id: 'x', created_at: '', workflow_id: 'w', mode: 'review', summary, waiting: {} });
  const review = (status: string) => ({ status }) as ReviewItem;

  test('adds up several runs', () => {
    const counts = overviewCounts(
      [run({ failed_validation: 6, skipped_duplicate: 1, review_pending: 1 }),
        run({ failed_error: 1, skipped_duplicate: 4, draft_saved: 4 })],
      [review('review_pending'), review('review_pending'), review('possible_duplicate')], 9);
    expect(counts).toEqual({ drafts: 9, waiting: 2, lookalike: 1, failed: 7, skipped: 5 });
  });

  test('nothing yet', () => {
    expect(overviewCounts([], [], 0)).toEqual({ drafts: 0, waiting: 0, lookalike: 0, failed: 0, skipped: 0 });
  });
});

describe('the train', () => {
  const nodes: WorkflowNode[] = ['validate', 'normalize', 'deduplicate', 'approval', 'persist']
    .map(id => ({ id, type: id }));
  const item = (...ids: string[]): Item => ({ source_id: 'L', status: 's', steps: ids,
    trace: ids.map(node => ({ node, type: node, input: {}, ms: 0, result: 'ok' as const })) });

  test('moves one station per tick and stops where the lesson stopped', () => {
    const waiting = item('validate', 'normalize', 'deduplicate', 'approval');
    expect([0, 1, 2, 3, 4, 9].map(n => trainStop(waiting, nodes, n))).toEqual([0, 1, 2, 3, 4, 4]);
    expect(arrived(waiting, 3)).toBe(false);
    expect(arrived(waiting, 4)).toBe(true);
  });

  test('a lesson that fails at validate stays at the first station', () => {
    expect(trainStop(item('validate'), nodes, 5)).toBe(1);
  });

  test('the longest lesson sets the length of the animation', () => {
    expect(ticksNeeded([item('validate'), item('validate', 'normalize', 'deduplicate')])).toBe(3);
    expect(ticksNeeded([])).toBe(0);
  });
});

describe('names and links', () => {
  test('workflow names from a key or an id', () => {
    expect(workflowName('dorosak_lessons', t)).toBe('Lesson intake');
    expect(workflowName('dorosak-content-intake', t)).toBe('Lesson intake');
    expect(workflowName('question-bank', t)).toBe('Question bank');
    expect(workflowName('something-else', t)).toBe('something-else');
  });

  test('samples and drafts files', () => {
    expect(sampleName('lessons_good', t)).toBe('Good lessons');
    expect(sampleName('upload:my_file', t)).toBe('Uploaded: my_file');
    expect(draftsFileWorkflow('python_drafts.json')).toBe('dorosak_lessons');
    expect(draftsFileWorkflow('python_question-bank_drafts.json')).toBe('question_bank');
  });

  test('hash links go there and back', () => {
    const { page, params } = parseHash(link('replay', { run: 'abc', i: '2' }));
    expect(page).toBe('replay');
    expect([params.get('run'), params.get('i')]).toEqual(['abc', '2']);
    expect(parseHash('').page).toBe('');
  });
});

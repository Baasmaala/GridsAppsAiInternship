import { describe, expect, test } from 'vitest';

import type { Item } from '../api/client';
import { askBody, askContext, sourceLine } from '../lib/ask';

const item: Item = { source_id: 'DOR-BAD-002', status: 'failed_validation', steps: ['validate'],
  trace: [{ node: 'validate', type: 'validate_lesson', input: {}, ms: 0, result: 'error' }] };
const last = { report: { items: [item] }, workflowKey: 'dorosak_lessons' };
const params = (q: string) => new URLSearchParams(q);

describe('what the panel looks at', () => {
  test('a saved run in Replay', () => {
    const ctx = askContext('replay', params('run=abc&i=2'), null);
    expect(ctx).toEqual({ kind: 'run', runId: 'abc', index: 2 });
    expect(askBody('  why?  ', 'en', ctx)).toEqual({ question: 'why?', lang: 'en', run_id: 'abc', index: 2 });
  });

  test('the last dry run sends the lesson itself, nothing else', () => {
    const ctx = askContext('replay', params('run=dry&i=0'), last);
    expect(ctx).toEqual({ kind: 'dry', item, workflow: 'dorosak_lessons', sourceId: 'DOR-BAD-002' });
    const body = askBody('why?', 'ar', ctx);
    expect(body).toEqual({ question: 'why?', lang: 'ar', item, workflow: 'dorosak_lessons' });
    expect('run_id' in body).toBe(false);
  });

  test('other pages and missing runs look at nothing', () => {
    expect(askContext('inbox', params('run=abc'), last)).toEqual({ kind: 'none' });
    expect(askContext('replay', params(''), null)).toEqual({ kind: 'none' });
    expect(askContext('replay', params('run=dry&i=9'), last)).toEqual({ kind: 'none' });
    expect(askBody('hi', 'en', { kind: 'none' })).toEqual({ question: 'hi', lang: 'en' });
  });

  test('the source line', () => {
    expect(sourceLine({ run: '5f9eeac8', lesson: 'DOR-CAT-004', station: 'approval', mode: 'templates' }))
      .toBe('run 5f9eeac8, DOR-CAT-004, approval, templates');
    expect(sourceLine({ run: null, lesson: null, station: 'check_duplicate', mode: 'templates' }))
      .toBe('check_duplicate, templates');
    expect(sourceLine({ run: 'what-if dry run', lesson: 'DOR-CAT-001', station: 'validate', mode: 'templates' }))
      .toBe('what-if dry run, DOR-CAT-001, validate, templates');
  });
});

import { describe, expect, test } from 'vitest';

import type { TraceEntry } from '../api/client';
import { SKIP_NOTES, skipReason } from '../lib/skip';
import py from '../../../masar/engine/nodes/flow_nodes.py?raw';
import mjs from '../../../masar/node/engine/nodes/flow_nodes.mjs?raw';

const skipped = (note: string): { status: string; trace: TraceEntry[] } => ({
  status: 'skipped_duplicate',
  trace: [
    { node: 'validate', type: 'validate_lesson', input: {}, ms: 0, result: 'ok' },
    { node: 'dupes', type: 'check_duplicate', input: {}, ms: 0, result: 'stop', status: 'skipped_duplicate', note },
  ],
});

describe('skip reason', () => {
  test('plain words for both kinds of skip', () => {
    expect(skipReason(skipped('source_id is already saved'))).toBe('skip.saved');
    expect(skipReason(skipped('source_id came earlier in this input'))).toBe('skip.earlier');
  });

  test('nothing for an unknown note or another status', () => {
    expect(skipReason(skipped('something new'))).toBeNull();
    expect(skipReason({ status: 'draft_saved', trace: [] })).toBeNull();
  });

  // if the engine text changes, this fails before the reason quietly goes missing
  test('the notes are still the ones both engines write', () => {
    for (const note of Object.keys(SKIP_NOTES)) {
      expect(py, `python engine: ${note}`).toContain(`"${note}"`);
      expect(mjs, `node engine: ${note}`).toContain(`'${note}'`);
    }
  });
});

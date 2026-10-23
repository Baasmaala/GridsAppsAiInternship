import { describe, expect, test } from 'vitest';

import { STATUSES, statusLook } from '../lib/status';
import { en } from '../i18n/strings';

// every status the engine can give (python masar/engine and node masar/node)
const ENGINE_STATUSES = ['dry_run_preview', 'review_pending', 'possible_duplicate', 'draft_saved',
  'skipped_duplicate', 'rejected', 'failed_validation', 'failed_error', 'complete'];

const PALETTE = ['var(--ok)', 'var(--wait)', 'var(--skip)', 'var(--fail)', 'var(--route)', 'var(--muted)'];

describe('status colors', () => {
  test('every engine status has a color and a word', () => {
    for (const s of ENGINE_STATUSES) {
      const look = statusLook(s);
      expect(look.word, s).not.toBeNull();
      expect(look.word! in en, s).toBe(true);
    }
    expect(Object.keys(STATUSES).sort()).toEqual([...ENGINE_STATUSES].sort());
  });

  test('colors come only from the palette', () => {
    for (const look of Object.values(STATUSES)) expect(PALETTE).toContain(look.color);
  });

  test('saved, waiting, skipped and failed use the plan colors', () => {
    expect(statusLook('draft_saved').color).toBe('var(--ok)');
    expect(statusLook('review_pending').color).toBe('var(--wait)');
    expect(statusLook('skipped_duplicate').color).toBe('var(--skip)');
    expect(statusLook('failed_validation').color).toBe('var(--fail)');
  });

  test('an unknown status still shows, in muted', () => {
    expect(statusLook('something_new')).toEqual({ color: 'var(--muted)', word: null });
  });
});

import type { Key } from '../i18n/strings';

// every status the engine can give, with its color and its short word
export const STATUSES = {
  draft_saved: { color: 'var(--ok)', word: 'status.saved' },
  review_pending: { color: 'var(--wait)', word: 'status.waiting' },
  possible_duplicate: { color: 'var(--wait)', word: 'status.lookalike' },
  dry_run_preview: { color: 'var(--route)', word: 'status.preview' },
  skipped_duplicate: { color: 'var(--skip)', word: 'status.skipped' },
  rejected: { color: 'var(--skip)', word: 'status.rejected' },
  failed_validation: { color: 'var(--fail)', word: 'status.failed' },
  failed_error: { color: 'var(--fail)', word: 'status.error' },
  complete: { color: 'var(--muted)', word: 'status.done' },
} as const satisfies Record<string, { color: string; word: Key }>;

export type Status = keyof typeof STATUSES;

export function statusLook(status: string): { color: string; word: Key | null } {
  if (status in STATUSES) return STATUSES[status as Status];
  return { color: 'var(--muted)', word: null };
}

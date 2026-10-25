import type { TraceEntry } from '../api/client';
import type { Key } from '../i18n/strings';

// the notes check_duplicate writes on a skip, in both engines. a test checks they still match.
export const SKIP_NOTES = {
  'source_id is already saved': 'skip.saved',
  'source_id came earlier in this input': 'skip.earlier',
} as const satisfies Record<string, Key>;

export function skipReason(item: { status: string; trace: TraceEntry[] }): Key | null {
  if (item.status !== 'skipped_duplicate') return null;
  const note = item.trace.find(e => e.status === 'skipped_duplicate')?.note ?? '';
  return note in SKIP_NOTES ? SKIP_NOTES[note as keyof typeof SKIP_NOTES] : null;
}

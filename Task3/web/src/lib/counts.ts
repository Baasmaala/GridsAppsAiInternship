import type { ReviewItem, RunSummary } from '../api/client';

export type OverviewCounts = { drafts: number; waiting: number; lookalike: number; failed: number; skipped: number };

// failed and skipped come from the run summaries, waiting from the inbox itself
export function overviewCounts(runs: RunSummary[], reviews: ReviewItem[], drafts: number): OverviewCounts {
  const sum = (status: string) => runs.reduce((n, r) => n + (r.summary[status] ?? 0), 0);
  return {
    drafts,
    waiting: reviews.filter(r => r.status === 'review_pending').length,
    lookalike: reviews.filter(r => r.status === 'possible_duplicate').length,
    failed: sum('failed_validation') + sum('failed_error'),
    skipped: sum('skipped_duplicate'),
  };
}

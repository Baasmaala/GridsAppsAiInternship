import { step } from '../context.mjs';

export function checkDuplicate(data, run) {
  const sid = data.source_id;
  if (run.knownIds.has(sid)) {
    return step(data, { status: 'skipped_duplicate', stop: true, note: 'source_id is already saved' });
  }
  if (run.seenIds.has(sid)) {
    return step(data, { status: 'skipped_duplicate', stop: true,
      note: 'source_id came earlier in this input' });
  }
  run.seenIds.add(sid);
  return step(data);
}

export function manualApproval(data, run) {
  if (!run.reviewer) {
    return step(data, { status: 'review_pending', stop: true, note: 'no reviewer name' });
  }
  return step(data, { note: `approved by ${run.reviewer}` });
}

export function saveDraft(data, run) {
  if (run.dryRun) return step(data, { status: 'dry_run_preview', note: 'dry run, nothing written' });
  if (!run.reviewer) {
    // lint already needs approval before this node. still: no name, no save
    return step(data, { status: 'review_pending', stop: true, note: 'no reviewer name' });
  }
  const draft = { ...data, status: 'draft', reviewed_by: run.reviewer, saved_at: run.now };
  run.newDrafts.push(draft);
  return step(draft, { status: 'draft_saved' });
}

export function logResult(data, run) {
  // only a marker for now, the audit file comes in phase 3
  return step(data);
}

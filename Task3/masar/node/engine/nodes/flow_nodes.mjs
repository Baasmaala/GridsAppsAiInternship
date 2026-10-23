import { step } from '../context.mjs';
import { fingerprint, printSource } from '../fingerprint.mjs';

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

  // new id, but maybe the same title. not skipped: a human decides.
  const { possible_duplicate_of: _old, ...clean } = data;
  const fp = fingerprint(printSource(clean));
  if (fp) {
    const other = run.knownPrints.get(fp) ?? run.seenPrints.get(fp);
    if (!run.seenPrints.has(fp)) run.seenPrints.set(fp, sid);
    if (other && other !== sid) {
      return step({ ...clean, possible_duplicate_of: other }, { note: `title looks like ${other}` });
    }
  }
  return step(clean);
}

export function manualApproval(data, run) {
  const other = data.possible_duplicate_of;
  if (other && !run.explicitItems.has(data.source_id)) {
    return step(data, { status: 'possible_duplicate', stop: true,
      note: `title looks like ${other}. a reviewer must approve this one by name` });
  }
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
  const fp = fingerprint(printSource(data));
  if (fp) draft.title_fingerprint = fp;
  run.newDrafts.push(draft);
  return step(draft, { status: 'draft_saved' });
}

export function logResult(data, run) {
  // only a marker. run files and the audit chain are in the python engine only.
  return step(data);
}

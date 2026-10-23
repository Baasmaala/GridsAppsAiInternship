from ..context import Step


def check_duplicate(data, run):
    sid = data["source_id"]
    if sid in run.known_ids:
        return Step(data, status="skipped_duplicate", stop=True, note="source_id is already saved")
    if sid in run.seen_ids:
        return Step(data, status="skipped_duplicate", stop=True,
                    note="source_id came earlier in this input")
    run.seen_ids.add(sid)
    return Step(data)


def manual_approval(data, run):
    if not run.reviewer:
        return Step(data, status="review_pending", stop=True, note="no reviewer name")
    return Step(data, note=f"approved by {run.reviewer}")


def save_draft(data, run):
    if run.dry_run:
        return Step(data, status="dry_run_preview", note="dry run, nothing written")
    if not run.reviewer:
        # lint already needs approval before this node. still: no name, no save
        return Step(data, status="review_pending", stop=True, note="no reviewer name")
    draft = {**data, "status": "draft", "reviewed_by": run.reviewer, "saved_at": run.now}
    run.new_drafts.append(draft)
    return Step(draft, status="draft_saved")


def log_result(data, run):
    # only a marker for now, the audit file comes in phase 3
    return Step(data)

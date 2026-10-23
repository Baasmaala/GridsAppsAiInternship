from ..context import Step
from ..fingerprint import fingerprint, print_source


def check_duplicate(data, run):
    sid = data["source_id"]
    if sid in run.known_ids:
        return Step(data, status="skipped_duplicate", stop=True, note="source_id is already saved")
    if sid in run.seen_ids:
        return Step(data, status="skipped_duplicate", stop=True,
                    note="source_id came earlier in this input")
    run.seen_ids.add(sid)

    # new id, but maybe the same title. not skipped: a human decides.
    data = {k: v for k, v in data.items() if k != "possible_duplicate_of"}
    fp = fingerprint(print_source(data))
    if fp:
        other = run.known_prints.get(fp) or run.seen_prints.get(fp)
        run.seen_prints.setdefault(fp, sid)
        if other and other != sid:
            return Step({**data, "possible_duplicate_of": other}, note=f"title looks like {other}")
    return Step(data)


def manual_approval(data, run):
    other = data.get("possible_duplicate_of")
    if other and data["source_id"] not in run.explicit_items:
        return Step(data, status="possible_duplicate", stop=True,
                    note=f"title looks like {other}. a reviewer must approve this one by name")
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
    fp = fingerprint(print_source(data))
    if fp:
        draft["title_fingerprint"] = fp
    run.new_drafts.append(draft)
    return Step(draft, status="draft_saved")


def log_result(data, run):
    # only a marker. the executor writes the audit line for every lesson,
    # also the ones that stop before this node.
    return Step(data)

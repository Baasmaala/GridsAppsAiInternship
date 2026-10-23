# Explain - the words from the brief

My short notes on each idea in the workshop, with an example from this project.

## The words

**Trigger** - what starts a run.
Here it is `manual`: I type the command in the terminal. (Later it could be a timer or a webhook.)
Example: `"trigger": {"type": "manual"}` in `workflow.json`.

**Workflow** - the list of steps, written as data in a JSON file.
Example: `dorosak-content-intake` = validate -> normalize -> deduplicate -> approval -> persist -> audit.

**Node** - one step with one job. Each node has an `id` (its name in this workflow)
and a `type` (which job it does).
Example: `{"id": "validate", "type": "validate_lesson"}` checks the fields and the CEFR level.

**Edge** - a link that says which node comes after which.
Example: `["validate", "normalize"]`. In this version the edges must be one straight line.

**Executor** - the part of the engine that walks the nodes in order and runs each one on the lesson.
Example: the `for node in nodes:` loop in `engine.py`.

**Context** - the data one lesson carries while it moves through the nodes.
Example: `ctx = {"data": {...lesson...}, "steps": [...], "status": "running"}`.
`normalize` replaces `data` with the cleaned lesson, and the next node gets that.

**State** - where a lesson is in its life right now.
Example: `review_pending` (waiting for a reviewer) or `draft_saved` (saved as a draft).

**Approval** - a human says yes before anything is saved.
Example: `--approved-by Trainer`. With no name, the lesson stops at `review_pending`.
The name is a test name, not a real login.

**Audit** - a record of what happened and when.
Example: each item in the report lists the `steps` it went through and its final `status`,
plus `run_id` and `generated_at` for the whole run.

**Dry run** - run everything but save nothing. Good to see what would happen.
Example: `--dry-run --approved-by Trainer` gives `dry_run_preview` and the output folder stays the same.

**Idempotency** - running the same thing twice gives the same end result, with no double records.
Example: the second approved run gives `skipped_duplicate`, because the `source_id` is already in the drafts file.

## Command -> status -> does it save?

From the brief, page 4. Run from the `starter` folder.

| Command | Status in the report | Saves? |
|---|---|---|
| `python python/engine.py --dry-run --approved-by Trainer` | `dry_run_preview` | No |
| `python python/engine.py` | `review_pending` | No |
| `python python/engine.py --approved-by Trainer` | `draft_saved` | Yes, as a local draft |
| same command again | `skipped_duplicate` | No new record |
| a lesson with an empty title | `failed_validation` | No |

The Node commands are the same with `node node/engine.mjs` and give the same statuses.

## Where the output goes

| Engine | File |
|---|---|
| Python | `output/python_drafts.json` |
| Node | `output/node_drafts.json` |

- The file is made only after an approved run (not dry run, reviewer name given).
- Every record in it has `"status": "draft"` and `"reviewed_by": "<name>"`. Draft means not published.
- The report itself is printed to the terminal, not saved.
- `--store <file>` puts the drafts file somewhere else (the tests use a temp folder).

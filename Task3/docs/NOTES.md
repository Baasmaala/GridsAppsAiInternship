# Notes

Things I found while reading the brief (PDF), PLAN.md and the starter code.
Rule: when they disagree, the starter and its tests win.

## 1. Status names

| Case | PDF (page 2, 4, 5) | Starter code and tests | PLAN.md |
|---|---|---|---|
| Dry run | `dry_run_preview` | `dry_run_preview` | - |
| No reviewer | `review_pending` | `review_pending` | `pending_review` |
| Approved | `draft_saved` | `draft_saved` | `saved_draft` |
| Run again | `skipped_duplicate` | `skipped_duplicate` | `duplicate_skipped` |
| Bad input | `failed_validation` | `failed_validation` | `validation_failed` |

The PDF and the starter agree. PLAN.md has the words in the wrong order.
I think this came from copying text out of the Arabic PDF: right-to-left text
flips words joined with `_`. The picture of the page shows the right names.

Masar uses the starter names: `dry_run_preview`, `review_pending`,
`draft_saved`, `skipped_duplicate`, `failed_validation`.

There is also a 6th status in the starter code: `complete`. It is set only if a
lesson passes every node and none of them set a status. With the normal
workflow this never happens.

## 2. Output file names

| | PDF (page 4) | Starter code | PLAN.md |
|---|---|---|---|
| Python | `output/python_drafts.json` | `output/python_drafts.json` | `output/drafts_python.json` |
| Node | `output/node_drafts.json` | `output/node_drafts.json` | `output/drafts_node.json` |

Same problem as above. Masar uses `python_drafts.json` and `node_drafts.json`.

## 3. "outcome" vs "status"

The PDF says to look for `outcome` for each lesson in `items`.
The starter report has no `outcome` key. Each item has `status`, and `summary`
counts how many items have each status. Masar keeps `status` (the starter tests check it).

## 4. CLI flags

PLAN.md says to add `--input`. The starter already has `--input` and also
`--store` (where the drafts file goes). The tests use `store` to work in a temp
folder. Masar must keep both flags.

## 5. Starter behaviour I need to remember

- **English only.** `validate_lesson` rejects any lesson where `language` is not `en`.
  Python says "Demo only accepts English lessons", Node says "Only English lessons allowed".
- **Arabic titles fail.** Even with `language: en`, an Arabic title gives
  "Cannot generate slug", because the slug only keeps `a-z` and `0-9`.
  PLAN.md wants Arabic word count (phase 1) and an Arabic duplicate fingerprint
  (phase 3). Decided: English only by default, see section 7.
- **Error messages are different** in Python and Node (the language one above).
  The parity check in phase 2 must compare status, not the error text, or Masar
  must use one shared message.
- **Validation lists all missing fields at once**, for example
  `Missing/empty field: title, category, body`. Good, keep it.
- **Level** is checked after trim and upper case: `" b1 "` is saved as `B1`, `9A` fails.
- **`status: "draft"` is added in `normalize_lesson`**, not in `save_draft`.
- **Approved run rewrites the file** even when nothing is new (second run).
  The content stays the same, so it is safe, but the file is still written.
- **Duplicates in the same input** are only caught in an approved run (the id is
  remembered after saving). In a dry run or a review run, two lessons with the same
  `source_id` both pass.
- **Python catches only `ValueError`, `KeyError`, `TypeError`** as `failed_validation`.
  Node catches every error.
- **Unknown node type or non-linear edges** stop the whole run with an error
  (no report). This is the starter's simple linter.
- **No lock** for two writers at the same time. The code says so in a comment.

## 6. Bugs I found in the starter

I do not change starter/. I fix these in masar, each with a test.

1. **Reviewer with only spaces gives the wrong mode.** `--approved-by "   "`:
   nothing is saved and every lesson is `review_pending`, which is right.
   But the report says `mode: "approved"`, because `mode` checks the name
   without trimming it. Both engines have it.
   Fix in masar: trim the name once at the start and use it everywhere.
   Test: spaces-only reviewer -> `review_pending`, nothing saved, `mode: "review"`.
2. **Python crashes if `normalize` runs before `validate`.** The `required` list is
   made only inside the validate branch, so normalize gets a `NameError`, which is
   not caught. Node does not have this bug.
   Fix in masar: required fields live in one place, outside any node, and the
   linter checks that validate comes before normalize.
3. **Python crashes on a lesson that is not an object.** Input `["hello", 5]`:
   `dict(raw)` runs before the `try`, so the whole run stops with a `ValueError`
   and no report. Node gives `failed_validation` for each item.
   Fix in masar: a non-object item is `failed_validation` ("Lesson must be an
   object") and the other lessons still run.

## 7. What masar does beyond the starter

**Status I added beyond the brief: `failed_error`.**
`failed_validation` means the lesson data is bad. `failed_error` means a node itself
broke (a bug, not bad input). That lesson stops, the other lessons still run, and the
error text says what broke, for example `RuntimeError: something broke`.
The starter would call both `failed_validation`, which hides real bugs as bad input.
The Node engine in phase 2 must use `failed_error` too.

Other changes (all have tests):
- **Same `source_id` twice in one input:** the second copy is `skipped_duplicate` in
  every mode (dry run, review, approved). The starter catches it only in an approved run.
- **Drafts file is written only when there is a new draft.** The starter rewrites it
  on every approved run.
- **`word_count` node** runs right after `normalize`. The count is in the draft and in
  the report item.
- **Allowed languages** come from `"allowed_languages"` in the workflow file (default `["en"]`).
- **Slug keeps letters from any language** (so an Arabic title gets an Arabic slug when
  `ar` is allowed). For plain English titles it is the same as the starter.
- **Extra report fields:** `workflow_version`, and on each item `word_count` and `trace`.
  The CLI hides `trace` unless you pass `--trace`. Drafts also get `saved_at`.
- **The linter refuses a workflow** with no `manual_approval` or no `check_duplicate`
  before `save_draft`. So a workflow file cannot skip the human.
- **Reading JSON accepts a BOM**, because PowerShell often saves files with one.

## 8. Decisions (23 Oct 2026)

- Keep the starter names and file names above. Keep `status`, not `outcome`.
- English only by default. In masar the allowed languages are a workflow setting:
  `"allowed_languages": ["en"]`.
- The title fingerprint (phase 3) works for English and Arabic titles.
- The parity check compares statuses only, not error messages.
- The PDF stays local. It is in .gitignore.

## 9. Folder

The starter folder is `Task3/Starter/` (capital S). The brief and PLAN.md use
`starter/` (small s). Windows does not care, but GitHub and Linux do, so a
CI job or a README path with `starter/` would break. Rename it to `starter/`.

# Self-check questions (page 6)

## 1. The difference between Trigger, Workflow, Node and Executor

- **Trigger:** what starts a run. In Masar it is manual: I type the command or press Run.
- **Workflow:** the plan, written as data. A JSON file with the list of stations and the lines
  between them. It says what should happen, but it runs nothing by itself.
- **Node:** one station with one job, like "validate" or "check duplicates". Its type must be on
  the allowlist, or the workflow is refused.
- **Executor:** the part of the engine that takes each lesson and moves it through the nodes in
  order, keeps the context and the trace, and decides the final status.

## 2. Why duplicate detection is one of the most important needs of an import system

Imports run again and again: a retry, a second click, the same file next week. Without a duplicate
check, every run makes the same lesson again, and people approve and publish copies. With it, a
second run is safe (`skipped_duplicate`). Masar also compares cleaned titles in English and Arabic,
because the same lesson can come back with a new id; it then asks a person instead of guessing.

## 3. How to stop AI output from being published without review

- The engine only saves drafts, never publishes.
- The approval station is in every workflow (the linter refuses a workflow without it before save).
- No reviewer name means nothing is saved, and from the web app a save happens only in the
  Review Inbox, one lesson at a time.
- Ask Masar, the only part that can use a model, has no function that writes, and an answer that
  says "I approved it" is not shown.

## 4. If an API fails with a timeout, do you retry? And if the title is empty?

- **Timeout (or 503):** yes, retry, because it may work next time. But wait longer each time
  (1s, 2s, 4s), stop after 3 retries, and respect `retry_after`. If the service says "try again
  in 13 hours", stop now instead of hammering it.
- **Empty title:** no. It will be empty every time. It is `failed_validation`, the reason is shown,
  and it is never retried. The error type decides, not the message.

## 5. Three additions the engine needs before company use

1. **Real login and roles**, so the reviewer is a known person and publishing needs a separate permission.
2. **A database with transactions and a unique index**, so duplicates are refused even when two
   writers race, and a draft, its run and its audit line are saved together.
3. **A queue with workers and a staging API**, so runs and retries happen in the background and
   drafts go to a test copy of Dorosak first, never straight to the live site.

# Roadmap: from this engine to a platform

The brief (page 6) lists six areas where the same idea could grow. For each one: what Masar already
gives, and what it would still need. The first list is needed by all of them.

## Needed by every area

1. **A database with a unique index** for drafts and runs, and transactions, so a duplicate is
   refused even when two writers race, and a draft, its run and its audit line are saved together.
2. **Real login and roles.** A reviewer is a person with an account, not a typed name. Approving
   and publishing are different permissions.
3. **A queue and workers**, so runs do not happen inside a web request, and a transient failure can
   wait and try again later without hammering the service.
4. **Workflow versions.** Every run points to the exact workflow version it used.
5. **Branches** in the workflow (if this, then that), still checked by the linter so no branch can
   skip the approval station.
6. **A safe place for the audit head** (a database row or a signed receipt), so a cut audit log is
   always found.
7. **A kill switch** that turns off every real write at once.

## The six areas

| Area | Example automations | Needs first (from the brief) | What Masar already gives | What is still missing |
|---|---|---|---|---|
| Dorosak | review lessons, categories, tests | editorial approval + staging API | validate, normalize, duplicate and look-alike check, human gate, drafts only, question bank workflow | a staging API to send drafts to, a separate publish step with its own permission, editor accounts |
| CRM | share out leads, move them between stages | permissions + business rules | allowlisted steps, rules in nodes, audit of every step | lead owner rules, access per team, branches (hot / cold lead), a connector to the CRM |
| ERP | match stock records, stock alerts | transaction rules + audit | tamper-evident audit chain, safe file writes, dry run | real database transactions, two-person approval for money and stock, exact decimal numbers |
| Sales / Marketing | make tasks, follow up campaigns | opt-in + rate limits | human gate before anything is sent, dry run to preview | opt-in check per contact, rate limits per channel, an unsubscribe list, scheduled triggers |
| Support | sort tickets, escalate them | privacy + reviewer | reviewer step, Ask Masar that only reads and explains | removing personal data before anything is logged or sent to a model, ticket system connector, time limits for escalation |
| Coding | open issues, CI reports | repo-scoped access + review | parity tests, CI workflow, review before anything is saved | a bot account with access to one repo only, pull requests instead of direct pushes, review by a person |

## Next steps for Masar itself

1. SQLite with a unique index on `(workflow_id, source_id)`, behind the same `read_store` / save functions.
2. Simple accounts for the web app, and the reviewer name taken from the account.
3. A "publish to staging" node that only runs after a second, separate approval.
4. Branches in the workflow file, with a linter rule that every path to `save_draft` passes approval.
5. Move resume and the audit chain to the Node engine too, so the parity check covers them.

# Grids Apps LLC | Automation Engine Workshop Starter

**A teaching prototype, not n8n and not a production integration.** Both versions read the same sample content and sequential workflow JSON. They validate, normalize, deduplicate, require simulated manual approval, and save records as **drafts only** into local sandbox JSON. Nothing reaches the Dorosak API or real database.

## Quick start (choose one)

From the `starter/` directory:

**Python 3.11+** (no pip packages):
```bash
python python/engine.py --dry-run --approved-by Trainer
python python/engine.py
python python/engine.py --approved-by Trainer
python python/engine.py --approved-by Trainer   # duplicates skipped
cd python && python -m unittest -v
```

**Node.js 20+** (no npm packages):
```bash
node node/engine.mjs --dry-run --approved-by Trainer
node node/engine.mjs
node node/engine.mjs --approved-by Trainer
node node/engine.mjs --approved-by Trainer      # duplicates skipped
cd node && node --test
```

## Files
- `shared/workflow.json`: a declarative **linear** nodes + edges model (not a full DAG engine)
- `shared/lessons.json`: synthetic Dorosak-like sample only
- `python/engine.py` and `node/engine.mjs`: comparable lightweight engines
- `python/test_engine.py`, `node/engine.test.mjs`: four baseline tests per implementation
- `output/*_drafts.json`: created locally when approved; contains `status: draft`

## Suggested lab experiments
1. Remove a title or use CEFR `A9`: verify `failed_validation` and no invalid content saved.
2. Run without `--approved-by`: verify `review_pending`, no write.
3. Run twice with `--approved-by Trainer`: verify duplicates skipped on second run.
4. Run `--dry-run --approved-by Trainer`: verify preview and no saved changes.
5. Add a new **approved** node type `word_count` in both registries and workflow before `save_draft`; extend tests.

## Real-world safeguards (not present in this PoC)
Authenticated role-based human approval, API authorization, webhook signature verification, encrypted secret storage, real transactions/concurrency locks, distributed job queues, retries/backoff with idempotency keys, audit database, rate limits, data retention controls, and production monitoring. Do not expose this demo to public networks or production systems.

**Note:** `--approved-by` is a simulated human sign-off, not an authentication mechanism. The engine is intentionally limited to a single linear workflow; branching/parallel execution and a visual canvas are future exercises.

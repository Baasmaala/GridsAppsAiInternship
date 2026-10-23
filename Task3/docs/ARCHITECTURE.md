# Architecture

## The parts

```mermaid
flowchart LR
  subgraph files["files (the contract)"]
    WF["masar/workflows/*.json<br/>nodes + edges"]
    SM["masar/samples/*.json<br/>sample lessons"]
  end
  subgraph engines["engines"]
    PY["Python engine<br/>masar/engine"]
    ND["Node.js engine<br/>masar/node"]
  end
  CLI["CLI<br/>python -m masar"] --> PY
  NCLI["CLI<br/>node masar/node/cli.mjs"] --> ND
  WF --> PY
  WF --> ND
  SM --> PY
  SM --> ND
  PY --> OUT["output/<br/>drafts, runs/, audit.jsonl"]
  ND --> NOUT["output/node_drafts.json"]
  API["FastAPI backend<br/>api/ (127.0.0.1 only)"] --> PY
  ASK["Ask Masar<br/>api/assistant (read only)"] -. reads .-> OUT
  ASK -. dry run only .-> PY
  API --> ASK
  WEB["web app<br/>React + Vite"] -- /api --> API
  PAR["tools/parity_check.py"] --> CLI
  PAR --> NCLI
```

- **The workflow file is the contract.** Both engines read the same JSON and give the same status
  for every lesson. `tools/parity_check.py` proves it on 7 cases.
- **The engine owns the rules.** Approval, drafts only and "dry run writes nothing" are in the
  engine. The CLI, the backend and the web app all go through it, so none of them can skip a rule.
- **Only the Python engine keeps state** (run files, resume, retry, audit chain), because the
  backend uses it. The Node engine has every node and linter rule, so it runs every workflow file.
- **Ask Masar** only reads runs and drafts. Its one engine call is a dry run with an empty temp store.

## One run

```mermaid
flowchart LR
  T(["manual start"]) --> L{"lint<br/>allowlist, keys,<br/>one straight line,<br/>approval before save"}
  L -- refused --> R["no lesson moves"]
  L -- ok --> V["validate"]
  V -- bad data --> FV["failed_validation<br/>(never retried)"]
  V --> N["normalize"] --> W["count words"] --> D["check duplicates"]
  D -- same source_id --> SD["skipped_duplicate"]
  D --> A{"approval<br/>(human gate)"}
  A -- no reviewer --> RP["review_pending<br/>run file saved"]
  A -- title looks the same --> PD["possible_duplicate<br/>run file saved"]
  RP -. resume / inbox .-> D
  PD -. approve this one by name .-> D
  A -- reviewer --> S["save draft"]
  S -- dry run --> DR["dry_run_preview<br/>nothing written"]
  S --> DS["draft_saved<br/>status: draft"]
  DS --> AU["audit log<br/>(every lesson gets a line)"]
```

- **A pause is saved state.** A lesson that waits for a person is written to `output/runs/<run_id>.json`
  and the program ends. A resume reads it later and starts again at the duplicate check, because
  another run may have saved the same lesson in the meantime.
- **Every station adds a line to the trace:** the data before and after, the time, and whether it
  went on, stopped or failed. Replay in the web app shows this, station by station.
- **Errors have types.** `ValidationError` (bad data) is never retried. `TransientError` (timeout,
  503) is retried after 1s, 2s, 4s, and a `retry_after` over 30s stops at once. A bug in a node is
  `failed_error`: that lesson stops, the others go on.
- **The audit log** gets one line per lesson and per decision. Each line keeps the hash of the line
  before it, and each run file keeps the last hash, so `verify-audit` finds an edited, removed or cut line.

## Where each safety rule lives

| Rule | Where |
|---|---|
| Only known node types run, no code in JSON | `masar/engine/lint.py` (allowlist in `registry.py`) |
| No save without approval before it | linter rule + `save_draft` also checks the reviewer name |
| No reviewer name, nothing saved | `executor.py` trims the name once, `manual_approval` stops |
| Dry run writes nothing | `executor.py`: everything that writes is behind `if not dry_run` |
| Every saved record is a draft | `save_draft` sets `status: "draft"` |
| From the web, saving only in the inbox | `api/service.py`: `approved_by` only with `dry_run` |
| Local only | `api/__main__.py` binds 127.0.0.1, trusted hosts, CORS only for the web app |
| Ask Masar cannot act | `api/assistant/` has no write function; a test reads its code |

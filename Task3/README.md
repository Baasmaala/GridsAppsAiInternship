# Masar (مسار)

Masar is a small automation engine for Dorosak lesson intake, built from the Grids Apps workshop
"Build Your Own Automation Engine" (21 Oct 2026). A workflow is a line of steps written in a JSON
file. Every lesson rides that line: validate, normalize, count words, check duplicates, wait for a
person, save a draft, write the audit log. It runs only on your computer, it never publishes
anything, and nothing is saved until a person approves it.

There are two engines (Python and Node.js) that read the same workflow file, a web app with a
review inbox, and a small read-only helper called Ask Masar.

Three rules that never change:
- **Drafts only.** Every saved record has `status: "draft"`. Nothing goes to the real Dorosak site.
- **A person decides.** No reviewer name means nothing is saved. The web app saves only from the Review Inbox.
- **Dry run writes nothing.** Not one file in `output/`.

---

## 1. Install the tools (once)

Open **PowerShell** and run these. If `winget` is not on your computer, use the links.

| Tool | Command | Link |
|---|---|---|
| Git | `winget install Git.Git` | https://git-scm.com/download/win |
| uv (Python tools, also installs Python 3.11) | `winget install astral-sh.uv` | https://docs.astral.sh/uv/ |
| Node.js 20 or newer | `winget install OpenJS.NodeJS.LTS` | https://nodejs.org |

Close PowerShell and open it again, so it finds the new tools. Then check:

```powershell
git --version
uv --version
node --version
```

## 2. Get the code

In any folder you like (for example your Desktop):

```powershell
git clone https://github.com/Baasmaala/GridsAppsAiInternship.git
cd GridsAppsAiInternship\Task3
```

All the commands below are run in this `Task3` folder, unless it says otherwise.

## 3. Install the packages

```powershell
uv sync
cd web
npm ci
cd ..
```

`uv sync` makes a `.venv` folder with Python 3.11, FastAPI and uvicorn. `npm ci` installs React,
Vite and the test tools for the web app. The engines themselves need no packages.

## 4. Try the command line

### The workshop starter (the brief, page 3 and 4)

```powershell
cd starter
python python/engine.py --dry-run --approved-by Trainer
python python/engine.py
python python/engine.py --approved-by Trainer
python python/engine.py --approved-by Trainer
node node/engine.mjs --dry-run --approved-by Trainer
node node/engine.mjs
node node/engine.mjs --approved-by Trainer
node node/engine.mjs --approved-by Trainer
cd ..
```

If `python` is not found, use `uv run python` instead.

### Masar (Python)

```powershell
uv run python -m masar --dry-run --approved-by Trainer   # dry_run_preview, nothing written
uv run python -m masar                                   # review_pending, waits for a person
uv run python -m masar --approved-by Trainer             # draft_saved
uv run python -m masar --approved-by Trainer             # skipped_duplicate
uv run python -m masar --input masar/samples/lessons_bad.json --dry-run --approved-by Trainer
uv run python -m masar --lint --workflow masar/workflows/malicious_example.json   # refused
uv run python -m masar --graph                           # the workflow as a Mermaid diagram
uv run python -m masar runs                              # runs with lessons waiting
uv run python -m masar resume --run <run id> --approved-by Mona
uv run python -m masar verify-audit                      # checks the audit hash chain
```

Drafts go to `output/python_drafts.json`. Add `--trace` to see every station, or
`--report-html report.html` for a page you can open in a browser.

### Masar (Node.js)

```powershell
node masar/node/cli.mjs --dry-run --approved-by Trainer
node masar/node/cli.mjs --approved-by Trainer
```

Same flags and the same statuses. Drafts go to `output/node_drafts.json`.

## 5. Run all the tests

```powershell
uv run python -m unittest
cd masar\node
node --test
cd ..\..\web
npm test
cd ..
```

All green looks like this: `Ran 186 tests ... OK` for Python, `pass 74 fail 0` for Node, and
`Tests 28 passed` for the web app. The Python run also runs the starter tests, the Node tests and
the parity check (both engines must give the same status for every lesson).

Two more checks you can run:

```powershell
uv run python tools/parity_check.py   # python vs node, 7 cases
uv run python tools/challenges.py     # the 5 workshop challenges
```

## 6. Start the web app

The easiest way: double-click **`start.bat`** in the `Task3` folder (after step 3).

It opens the backend in a second window, waits until it answers, starts the website and opens it in
your browser. To stop, close both windows (or press Ctrl+C in each).

The same thing from PowerShell, in the `Task3` folder (add `-Open` to also open the browser):

```powershell
powershell -ExecutionPolicy Bypass -File tools\dev.ps1
```

Or do it by hand in two PowerShell windows:

```powershell
# window 1, in Task3
uv run python -m api
# window 2, in Task3\web
npm run dev
```

Then open **http://127.0.0.1:5173** in your browser. Stop with Ctrl+C in each window.

A first demo: on **Overview** press "Reset demo" (keep "seed" on), open the **Review Inbox**, type a
name and approve a lesson, then look at **Drafts** and press **Verify** in the **Audit Log**.
`DEMO.md` has a 5 minute script.

## 7. Ask Masar with a real model (optional)

Ask Masar works without any key: it answers from the run report and the trace (`FAKE_MODEL=1`).
To try a real model:

```powershell
copy .env.example .env
notepad .env
```

Set `FAKE_MODEL=0` and put your key after `GEMINI_API_KEY=`. Restart the backend. `.env` is never
committed. Ask Masar can only read: it cannot approve, reject or save anything.

## 8. If something goes wrong

| Problem | What to do |
|---|---|
| `running scripts is disabled on this system` | Start the script with `powershell -ExecutionPolicy Bypass -File tools\dev.ps1` |
| `Port 8001 is already in use` / `Port 5173 is already in use` | Another program uses it. Close it, or set another port for the backend: `$env:MASAR_PORT = "8011"` in both windows |
| The browser shows a different app | Open `http://127.0.0.1:5173`, not `localhost:5173` |
| `Cannot reach the Masar API` in the web app | The backend is not running. Start `uv run python -m api` |
| `python` is not found | Use `uv run python ...` |

## Where things are

```
starter/     the workshop starter, unchanged
masar/       the engine: Python in masar/engine, Node.js in masar/node, workflows, samples, tests
api/         the FastAPI backend (127.0.0.1 only) and Ask Masar
web/         the React web app
tools/       parity check, challenge runner, dev.ps1
docs/        EXPLAIN, NOTES, ARCHITECTURE, LIMITATIONS, ROADMAP, SELF_CHECK
REPORT.md    the report for the team
DEMO.md      a 5 minute demo script
```

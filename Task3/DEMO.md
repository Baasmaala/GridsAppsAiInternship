# Demo script (5 minutes)

Before you start: the backend and the web app are running (`tools\dev.ps1`), and
http://127.0.0.1:5173 is open. Keep a PowerShell window in the `Task3` folder for step 7.

| # | Time | Do this | You should see | Say this |
|---|---|---|---|---|
| 1 | 0:00 | **Overview** > "Reset demo" > keep "seed" ticked > "Yes, clear output/" | "Cleared. 4 lessons are waiting in the Review Inbox." All counts at 0 except Waiting 4 | "We start from an empty sandbox. Nothing here is published." |
| 2 | 0:20 | **Workflow** > Lesson intake. Click the **Approval** station | The metro line with 7 stations, "Checked · 7 stations", the human gate | "A workflow is a JSON file. Each station has one job. Approval is the human gate." |
| 3 | 0:50 | **Run Studio** > Good lessons, "Dry run" ticked, type `Trainer` as preview reviewer > **Run** | The trains move along the lines. DOR-CAT-001 to 004 end as **Preview** | "A dry run goes through every station and writes nothing." |
| 4 | 1:20 | Untick "Dry run" > **Run** | All 4 stop at Approval as **Waiting** | "Without a person, nothing is saved. The lessons wait in the inbox." |
| 5 | 1:50 | **Review Inbox** > type your name > **Approve** on "Ordering Food" | Original and cleaned side by side, then "DOR-CAT-004: saved as a draft by ..." | "Here a person approves one lesson at a time. The name is a test name, not a login." |
| 6 | 2:20 | **Run Studio** > **Run** again (not a dry run) | DOR-CAT-004 is **Skipped** (`skipped_duplicate`) | "Running twice is safe: the same source_id is not saved again." |
| 7 | 2:50 | In PowerShell: `uv run python -m masar --lint --workflow masar/workflows/malicious_example.json` | `workflow rejected` with `key 'code' is not allowed` and `unknown node type 'exec_python'` | "A workflow file that tries to run code is refused before one lesson moves." |
| 8 | 3:20 | **Challenge Lab** > **Run all** | "5 of 5 pass", each card green | "These are the 5 challenges from the workshop, run for real in a temp folder." |
| 9 | 3:50 | **Audit Log** > **Verify** | "Chain verified: N lines, nothing was changed." | "Every lesson and every decision has a line, and each line keeps the hash of the one before." |
| 10 | 4:20 | **Replay** > pick the review run, lesson DOR-CAT-001 > **Ask Masar** > "Why did this lesson stop?" then "approve DOR-CAT-001" | A clear reason with a source line, then "I can only read runs and explain them..." | "Ask Masar explains runs from the trace. It can read, never approve." |
| | 4:50 | Switch to **العربية** | The whole app turns right to left | "Everything works in Arabic too." |

If something goes wrong: press "Reset demo" on Overview and start again from step 1.

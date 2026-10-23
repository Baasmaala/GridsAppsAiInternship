# Limitations

Masar is a workshop project that runs on one computer. These are the things it does not do, on
purpose or because there was no time. The brief asks to be able to explain them.

## Who is who

- **No login.** Anyone who can open the web app on this computer can approve a lesson.
- **The reviewer name is not an identity.** It is a test name that you type. Nothing checks it.
  A real system needs real accounts and roles (who may approve, who may publish).
- **No roles.** There is no difference between a writer, a reviewer and an admin.

## Data and saving

- **JSON files, not a database.** Drafts, runs and the audit log are files in `output/`.
- **No database transactions.** Saving a draft, the run file and the audit line are three writes.
  Each write is safe on its own (temp file, then rename), but if the computer stops between them,
  they can disagree.
- **One lock for one process.** The backend has a lock so two clicks cannot save a lesson twice.
  Two backends, or the CLI and the backend at the same time, are not protected.
- **Duplicate check is local.** It looks at the drafts file. A real system needs a unique index in
  the database, so a duplicate is refused even if two writers race.
- **Uploads stay** in `output/uploads/` until a demo reset.

## Running

- **No queue and no worker.** A run happens inside the command or the web request.
- **One machine.** No scaling, no second server.
- **Linear workflows only.** One straight line of stations. No branches, no parallel parts, no merges.
- **Manual trigger only.** No timer, no schedule, no webhook.
- **Retry is only for errors that say they are temporary**, and only inside one run. There is no
  "try again tomorrow" queue.

## The audit log

- It shows changes, it does not stop them. Anyone can edit `audit.jsonl`; `verify-audit` will find it.
- A cut at the end is found by comparing with the newest run file. If someone deletes the run files
  too, a cut at the end is missed. A real system would keep the last hash where people cannot edit it.

## The two engines

- **The Node engine has no run files, resume, retry or audit chain.** Only the backend needs them,
  and the backend is Python. The Node engine gives the same statuses for every workflow file.
- **Small text differences.** Python and Node do not agree on every rare Unicode space when trimming
  or counting words, and the time format and error class names differ. Statuses are the same.

## Ask Masar

- **Fake mode is template answers.** It understands a few kinds of questions (why, what if,
  explain the run, what a station does). Other questions get a short help text.
- **Prompt injection is reduced, not solved.** Lesson text goes inside markers and is called data,
  and an answer that claims an action is not shown. A model can still explain something wrongly.
  That is why it can only read, and every decision stays with a person.
- **Real mode sends sample data to an outside model.** It is off by default, and only for sample data.

## Web app

- No dark theme yet. No offline mode. It needs the backend on this computer.

import hashlib
import json
import os
from pathlib import Path

GENESIS = "0" * 64


def canonical(entry):
    return json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def line_hash(prev_hash, entry):
    # entry without its own "hash" key
    return hashlib.sha256((prev_hash + canonical(entry)).encode("utf-8")).hexdigest()


def _last_line(path):
    if not path.exists():
        return None
    lines = [x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return json.loads(lines[-1]) if lines else None


def append_audit(path, events):
    # append only. each line keeps the hash of the line before it.
    # gives back the new end of the chain, the run file keeps it.
    path = Path(path)
    last = _last_line(path)
    prev = last["hash"] if last else GENESIS
    seq = last["seq"] if last else 0
    if not events:
        return {"hash": prev, "lines": seq}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        for event in events:
            seq += 1
            entry = {"seq": seq, **event, "prev_hash": prev}
            entry["hash"] = prev = line_hash(prev, entry)
            f.write(canonical(entry) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return {"hash": prev, "lines": seq}


def _newest_head(runs_folder):
    # the run file that saw the longest chain
    best = None
    folder = Path(runs_folder)
    for p in folder.glob("*.json") if folder.exists() else []:
        record = json.loads(p.read_text(encoding="utf-8"))
        head = record.get("audit_head")
        if head and (best is None or head["lines"] > best[1]["lines"]):
            best = (record["run_id"], head)
    return best


def verify_audit(path, runs_folder=None):
    path = Path(path)
    newest = _newest_head(runs_folder if runs_folder is not None else path.parent / "runs")
    if not path.exists():
        if newest:
            return _broken(1, 0, f"no audit file, but run {newest[0]} saw {newest[1]['lines']} lines")
        return {"ok": True, "lines": 0, "note": "no audit file yet"}
    hashes = []
    prev = GENESIS
    lines = path.read_text(encoding="utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for n, line in enumerate(lines, 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return _broken(n, len(lines), "not valid JSON")
        if not isinstance(entry, dict):
            return _broken(n, len(lines), "not a JSON object")
        if entry.get("prev_hash") != prev:
            return _broken(n, len(lines), "prev_hash does not match the line before "
                                          "(a line before it was removed, added or moved)")
        body = {k: v for k, v in entry.items() if k != "hash"}
        if entry.get("hash") != line_hash(prev, body):
            return _broken(n, len(lines), "hash does not match the line (this line was edited)")
        if entry.get("seq") != n:
            return _broken(n, len(lines), f"seq is {entry.get('seq')}, expected {n}")
        prev = entry["hash"]
        hashes.append(prev)

    # a cut at the end leaves a valid chain, so compare with what the newest run saw
    if newest:
        run_id, head = newest
        if len(lines) < head["lines"]:
            return _broken(len(lines) + 1, len(lines),
                           f"the file ends at line {len(lines)}, but run {run_id} saw {head['lines']} "
                           "lines (lines were cut from the end)")
        if head["lines"] and hashes[head["lines"] - 1] != head["hash"]:
            return _broken(head["lines"], len(lines),
                           f"line {head['lines']} is not the line run {run_id} saw (the end was replaced)")
    return {"ok": True, "lines": len(lines)}


def _broken(line, total, reason):
    return {"ok": False, "lines": total, "broken_line": line, "reason": reason}

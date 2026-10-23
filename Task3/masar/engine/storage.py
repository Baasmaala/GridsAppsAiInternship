import json
import os
import tempfile
from pathlib import Path

from .errors import StoreError


def read_store(path):
    path = Path(path)
    if not path.exists():
        return []
    try:
        saved = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as ex:
        raise StoreError(f"drafts file is not valid JSON: {path} ({ex})") from None
    if not isinstance(saved, list):
        raise StoreError(f"drafts file must contain a JSON array: {path}")
    return saved


def atomic_json_write(path, value):
    # write a temp file next to it, then rename. no half-written json.
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(value, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise

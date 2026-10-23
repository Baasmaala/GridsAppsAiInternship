import time
from dataclasses import dataclass, field
from typing import Callable


# what a node gives back
@dataclass
class Step:
    data: object
    status: str | None = None
    stop: bool = False
    note: str | None = None


# shared by all lessons in one run
@dataclass
class Run:
    reviewer: str
    dry_run: bool
    allowed_languages: list[str]
    now: str
    known_ids: set[str] = field(default_factory=set)
    seen_ids: set[str] = field(default_factory=set)
    known_prints: dict[str, str] = field(default_factory=dict)  # fingerprint -> source_id
    seen_prints: dict[str, str] = field(default_factory=dict)
    explicit_items: set[str] = field(default_factory=set)  # approved one by one in a resume
    new_drafts: list[dict] = field(default_factory=list)
    sleep: Callable[[float], None] = time.sleep

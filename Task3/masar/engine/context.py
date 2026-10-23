from dataclasses import dataclass, field


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
    new_drafts: list[dict] = field(default_factory=list)

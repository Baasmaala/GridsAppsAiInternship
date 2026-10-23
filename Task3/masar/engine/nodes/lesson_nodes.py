import re
import unicodedata

from ..context import Step
from ..errors import ValidationError

REQUIRED = ("source_id", "title", "category", "level", "language", "body")
LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


def is_text(value):
    return isinstance(value, str) and value.strip() != ""


def one_line(text):
    return re.sub(r"\s+", " ", text).strip()


def slugify(text):
    # keep letters, marks and digits from any language, the rest becomes "-"
    chars = [ch if unicodedata.category(ch)[0] in "LMN" else " " for ch in text.lower()]
    return "-".join("".join(chars).split())


def validate_lesson(data, run):
    if not isinstance(data, dict):
        raise ValidationError("Lesson must be an object")
    missing = [k for k in REQUIRED if not is_text(data.get(k))]
    if missing:
        raise ValidationError("Missing/empty field: " + ", ".join(missing))

    problems = []
    if data["level"].strip().upper() not in LEVELS:
        problems.append(f"Invalid CEFR level '{data['level']}' (use {', '.join(LEVELS)})")
    if data["language"].strip().lower() not in run.allowed_languages:
        problems.append(f"Language '{data['language']}' is not allowed "
                        f"(allowed: {', '.join(run.allowed_languages)})")
    tags = data.get("tags")
    if tags is not None and not (isinstance(tags, list) and all(isinstance(t, str) for t in tags)):
        problems.append("tags must be a list of strings")
    if problems:
        raise ValidationError("; ".join(problems))
    return Step(data)


def clean_tags(tags):
    out = []
    for tag in tags:
        tag = one_line(tag).lower()
        if tag and tag not in out:
            out.append(tag)
    return out


def normalize_lesson(data, run):
    d = {k: data[k].strip() for k in REQUIRED}
    # body keeps its own spacing and lines, only trimmed
    d["title"] = one_line(d["title"])
    d["category"] = one_line(d["category"])
    d["level"] = d["level"].upper()
    d["language"] = d["language"].lower()
    if data.get("tags") is not None:
        d["tags"] = clean_tags(data["tags"])
    d["slug"] = slugify(d["title"])
    d["status"] = "draft"
    if not d["slug"]:
        raise ValidationError("Cannot generate slug from title")
    return Step(d)


def word_count(data, run):
    body = data.get("body") if isinstance(data, dict) else None
    if not isinstance(body, str):
        raise ValidationError("word_count needs a text body")
    return Step({**data, "word_count": len(body.split())})

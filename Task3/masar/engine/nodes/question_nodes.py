from ..context import Step
from ..errors import ValidationError
from .lesson_nodes import LEVELS, is_text, one_line

FIELDS = ("source_id", "question", "options", "answer", "level", "topic")
TEXT_FIELDS = ("source_id", "question", "level", "topic")


def validate_question(data, run):
    if not isinstance(data, dict):
        raise ValidationError("Question must be an object")
    missing = [k for k in FIELDS
               if (k in TEXT_FIELDS and not is_text(data.get(k))) or (k not in TEXT_FIELDS and data.get(k) is None)]
    if missing:
        raise ValidationError("Missing/empty field: " + ", ".join(missing))

    problems = []
    options = data["options"]
    if not isinstance(options, list) or len(options) != 4:
        got = len(options) if isinstance(options, list) else type(options).__name__
        problems.append(f"options must be a list of exactly 4 answers (got {got})")
    else:
        empty = [str(i + 1) for i, o in enumerate(options) if not is_text(o)]
        if empty:
            problems.append(f"option {', '.join(empty)} is empty")
        else:
            seen = [one_line(o).lower() for o in options]
            repeated = sorted({o for o in seen if seen.count(o) > 1})
            if repeated:
                problems.append(f"options repeat: {', '.join(repeated)}")
    answer = data["answer"]
    if isinstance(answer, bool) or not isinstance(answer, int) or not 0 <= answer <= 3:
        problems.append(f"answer must be the number of the right option, 0 to 3 (got {answer!r})")
    if data["level"].strip().upper() not in LEVELS:
        problems.append(f"Invalid CEFR level '{data['level']}' (use {', '.join(LEVELS)})")
    if problems:
        raise ValidationError("; ".join(problems))
    return Step(data)


def normalize_question(data, run):
    # keep only the known fields, trimmed
    d = {
        "source_id": data["source_id"].strip(),
        "question": one_line(data["question"]),
        "options": [one_line(o) for o in data["options"]],
        "answer": data["answer"],
        "level": data["level"].strip().upper(),
        "topic": one_line(data["topic"]),
        "status": "draft",
    }
    return Step(d)

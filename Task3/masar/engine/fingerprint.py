import hashlib
import re
import unicodedata

from .nodes.lesson_nodes import is_text

TASHKEEL = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")  # + tatweel
LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي"})


def clean_for_compare(text):
    # only for comparing. the stored text is never changed.
    text = TASHKEEL.sub("", unicodedata.normalize("NFKC", text)).translate(LETTERS).lower()
    chars = [" " if unicodedata.category(ch)[0] in "PSZC" else ch for ch in text]
    return " ".join("".join(chars).split())


def fingerprint(text):
    if not isinstance(text, str):
        return None
    cleaned = clean_for_compare(text)
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest() if cleaned else None


def print_source(data):
    # lessons have a title, questions have a question
    if not isinstance(data, dict):
        return None
    for key in ("title", "question"):
        if is_text(data.get(key)):
            return data[key]
    return None

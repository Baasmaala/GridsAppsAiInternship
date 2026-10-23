# the real model. one call per message. 429: no retry. 503: wait 5s, one more try.
import json
import re
import time
import urllib.error
import urllib.request

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT = 20
BUSY_WAIT = 5


def http_post(url, headers, body, timeout=TIMEOUT):
    # returns (status, bytes). 0 means no answer at all (no network, timeout)
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as ex:
        return ex.code, ex.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, b""


def ask(system, user, cfg, *, post=http_post, sleep=time.sleep):
    if not cfg.get("key"):
        return {"text": None, "error": "no_key", "calls": 0}
    body = json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400},
        # no tools: the model can only give text back
    }).encode("utf-8")
    headers = {"Content-Type": "application/json", "x-goog-api-key": cfg["key"]}
    url = URL.format(model=cfg["model"])

    calls = 0
    for attempt in (1, 2):
        calls += 1
        status, raw = post(url, headers, body)
        if status == 200:
            return {"text": _text(raw), "error": None if _text(raw) else "empty", "calls": calls}
        if status == 429:
            return {"text": None, "error": "quota", "calls": calls}  # never retry a 429
        if status == 503 and attempt == 1:
            sleep(BUSY_WAIT)
            continue
        return {"text": None, "error": "busy" if status == 503 else "failed", "calls": calls}
    return {"text": None, "error": "busy", "calls": calls}


def _text(raw):
    try:
        data = json.loads(raw)
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip() or None
    except (ValueError, KeyError, IndexError, TypeError):
        return None


CLAIM_EN = re.compile(r"\b(i|we)\s+(have\s+)?(approved|rejected|saved|published|deleted)\b|"
                      r"\b(has|have|was|were|is now|are now)\s+(been\s+)?(approved|published|saved|deleted)\b", re.I)
CLAIM_AR = re.compile(r"تمت الموافقة|وافقت على|تم الحفظ|حفظت|تم النشر|نشرت|تم الحذف|حذفت")
PUBLISH = re.compile(r"publish|نشر", re.I)


def claims_action(text, saved_is_true):
    # the model must not say it did something. "saved" is only fine when the lesson really is a saved draft.
    if PUBLISH.search(text) and (CLAIM_EN.search(text) or CLAIM_AR.search(text)):
        return True
    return bool(CLAIM_EN.search(text) or CLAIM_AR.search(text)) and not saved_is_true

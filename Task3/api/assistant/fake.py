# FAKE_MODEL=1: answers built from the run report and the trace with simple templates.
# no model, no network. also used as the facts we give the real model.
import copy
import re

from .context import default_workflow, pick_item, sample_lesson, what_if
from .knowledge import MODES, STATION_WORDS, STATIONS, STATUS, station_label

LESSON_ID = re.compile(r"\b[A-Z]{2,}(?:-[A-Z0-9]+)+\b")
WH = re.compile(r"\b(why|what|how|when|which|does|do)\b|لماذا|ماذا|كيف|متى|هل|^ما\b|ما هي|ما وظيفة")
POLITE = re.compile(r"\b(can you|could you|please|go ahead)\b|يمكنك|ممكن|من فضلك|لو سمحت")
ACTION = re.compile(r"\b(approve|reject|save|publish|delete|remove|accept|edit|change)\b|وافق|ارفض|احفظ|انشر|احذف|اعتمد|عدّل|غيّر")
WHAT_IF = re.compile(r"what if|what happens if|what would happen if|suppose|ماذا لو|ماذا يحدث لو|ماذا يحدث إذا|ماذا يحدث اذا|لو كان")
WHY = re.compile(r"\bwhy\b|what happened|\bstop|\bfail|لماذا|ماذا حدث|توقف|فشل")
NODE_Q = re.compile(r"what does|what do|what is|explain the|ماذا يفعل|ماذا تفعل|ما وظيفة|ما هي|ما هو|اشرح محطة")
EXPLAIN_RUN = re.compile(r"explain|summar|overview|this run|اشرح|لخص|التشغيل|ملخص")

FIELD_WORDS = {
    "level": ["level", "المستوى"], "title": ["title", "العنوان"], "language": ["language", "اللغة"],
    "category": ["category", "الفئة", "التصنيف"], "body": ["body", "النص"], "source_id": ["source_id"],
    "question": ["question", "السؤال"], "topic": ["topic", "الموضوع"], "answer": ["answer", "الجواب", "الإجابة"],
}
FIELD_NAMES = {
    "en": {"level": "the level", "title": "the title", "language": "the language", "category": "the category",
           "body": "the body", "question": "the question", "topic": "the topic", "answer": "the answer"},
    "ar": {"level": "المستوى", "title": "العنوان", "language": "اللغة", "category": "الفئة", "body": "النص",
           "question": "السؤال", "topic": "الموضوع", "answer": "الجواب"},
}
EMPTY = {"empty", "blank", "nothing", "none", "فارغ", "فارغا", "فارغة", "فاضي"}
CONNECTORS = re.compile(r"^\s*(?:is|was|were|=|:|becomes|became|be|set to|to|equal to|كان|كانت|هو|هي|يساوي|تساوي)\s*")

WORKFLOW_NAMES = {"dorosak-content-intake": {"en": "Lesson intake", "ar": "استقبال الدروس"},
                  "question-bank": {"en": "Question bank", "ar": "بنك الأسئلة"}}

T = {
    "refuse": {"en": "I can only read runs and explain them. I cannot approve, reject, save, publish or delete "
                     "anything. To decide about a lesson, use the Review Inbox, where a person types their name.",
               "ar": "أنا أقرأ التشغيلات وأشرحها فقط. لا يمكنني الموافقة أو الرفض أو الحفظ أو النشر أو الحذف. "
                     "لتقرر في درس، استخدم صندوق المراجعة، حيث يكتب شخص اسمه."},
    "help": {"en": "I can answer questions like: why did a lesson stop, explain this run, what happens if the "
                   "level is 9A, or what a station does. Open a lesson in Replay, or name a lesson in your "
                   "question (for example DOR-CAT-004).",
             "ar": "يمكنني الإجابة عن أسئلة مثل: لماذا توقف درس، اشرح هذا التشغيل، ماذا يحدث لو كان المستوى 9A، "
                   "أو ماذا تفعل محطة. افتح درسا في إعادة العرض، أو اذكر اسم الدرس في سؤالك (مثل DOR-CAT-004)."},
    "need_lesson": {"en": "Open a lesson in Replay first, or name it in the question, like DOR-CAT-004.",
                    "ar": "افتح درسا في إعادة العرض أولا، أو اذكره في السؤال، مثل DOR-CAT-004."},
    "not_found": {"en": "I could not find {sid} in the saved runs. Check the id, or open the run in Replay.",
                  "ar": "لم أجد {sid} في التشغيلات المحفوظة. تأكد من الاسم، أو افتح التشغيل في إعادة العرض."},
    "need_run": {"en": "Open a run in Replay first, then ask again.",
                 "ar": "افتح تشغيلا في إعادة العرض أولا، ثم اسأل مرة أخرى."},
    "no_field": {"en": "Tell me which field to change and the new value, for example: what happens if the level is 9A?",
                 "ar": "قل لي أي حقل تريد تغييره والقيمة الجديدة، مثلا: ماذا يحدث لو كان المستوى 9A؟"},
    "stopped": {"en": "{sid} stopped at {station} ({type}) with {status}: {meaning}",
                "ar": "توقف {sid} عند محطة {station} ({type}) بحالة {status}: {meaning}"},
    "went": {"en": "{sid} went through the line and ended with {status}: {meaning}",
             "ar": "مر {sid} على الخط وانتهى بحالة {status}: {meaning}"},
    "error": {"en": " The exact reason: {error}.", "ar": " السبب بالضبط: {error}."},
    "words": {"en": " The body has {n} words.", "ar": " في النص {n} كلمات."},
    "run": {"en": "Run {run} ({workflow}, {mode}) has {n} lessons: {counts}. {lines}.",
            "ar": "التشغيل {run} ({workflow}، {mode}) فيه {n} دروس: {counts}. {lines}."},
    "dry_run_name": {"en": "the last dry run", "ar": "آخر تشغيل تجريبي"},
    "what_if": {"en": "If {field} is '{value}', the lesson {outcome} I checked this with a dry run of the real "
                      "engine on a copy of {base}. Nothing was saved.",
                "ar": "لو كان {field} '{value}'، فإن الدرس {outcome} تحققت من ذلك بتشغيل تجريبي للمحرك الحقيقي على "
                      "نسخة من {base}. لم يُحفظ أي شيء."},
    "wi_stop": {"en": "stops at {station} with {status}: {error}.", "ar": "يتوقف عند محطة {station} بحالة {status}: {error}."},
    "wi_pass": {"en": "passes every station ({status}).", "ar": "يمر على كل المحطات ({status})."},
    "wi_other": {"en": "ends at {station} with {status}.", "ar": "ينتهي عند محطة {station} بحالة {status}."},
    "node": {"en": "{label} ({type}) {text}", "ar": "{label} ({type}) {text}"},
}


ARABIC = re.compile(r"[؀-ۿ]")
LATIN = re.compile(r"[A-Za-z]")


def pick_lang(question, lang):
    # "in english" / "بالعربية" wins. then the language the question is written in. then the page.
    q = question.lower()
    if "in arabic" in q or "بالعربية" in question or "بالعربي" in question:
        return "ar"
    if "in english" in q or "بالإنجليزية" in question or "بالانجليزية" in question:
        return "en"
    words = LESSON_ID.sub("", question)  # lesson ids are latin in both languages
    arabic, latin = len(ARABIC.findall(words)), len(LATIN.findall(words))
    if arabic or latin:
        return "ar" if arabic >= latin else "en"
    return lang if lang in ("en", "ar") else "en"


def is_action_request(question):
    q = question.lower()
    return bool(ACTION.search(q)) and (not WH.search(q) or bool(POLITE.search(q)))


def station_in(question):
    q = question.lower()
    for node_type, words in STATION_WORDS.items():
        if any(w in q for w in words):
            return node_type
    return None


def source(ctx, item=None, node=None):
    run = "dry run" if ctx.dry else (ctx.run_id[:8] if ctx.run_id else None)
    return {"run": run, "lesson": str(item["source_id"]) if item else None, "station": node}


def explain_item(item, lang):
    last = item["trace"][-1] if item.get("trace") else {}
    status = item["status"]
    meaning = STATUS.get(status, {}).get(lang, status).format(dup=item.get("possible_duplicate_of", ""))
    stopped = last.get("result") in ("stop", "error")
    key = "stopped" if stopped else "went"
    text = T[key][lang].format(sid=item["source_id"], station=station_label(last.get("type", ""), lang),
                               type=last.get("type", ""), status=status, meaning=meaning)
    if item.get("error"):
        text += T["error"][lang].format(error=item["error"])
    if isinstance(item.get("word_count"), int):
        text += T["words"][lang].format(n=item["word_count"])
    return text, last.get("node")


def explain_run(ctx, lang):
    report = ctx.report
    counts = "، ".join if lang == "ar" else ", ".join
    count_text = counts(f"{s} {n}" for s, n in report["summary"].items())
    lines = ("؛ " if lang == "ar" else "; ").join(f"{i['source_id']}: {i['status']}" for i in report["items"][:12])
    workflow = WORKFLOW_NAMES.get(report["workflow_id"], {}).get(lang, report["workflow_id"])
    return T["run"][lang].format(run=report["run_id"][:8] if not ctx.dry else T["dry_run_name"][lang],
                                 workflow=workflow, mode=MODES.get(report["mode"], {}).get(lang, report["mode"]),
                                 n=len(report["items"]), counts=count_text, lines=lines)


def parse_change(question, base):
    q = question
    for field, words in FIELD_WORDS.items():
        if field not in base:
            continue
        for word in words:
            at = q.lower().find(word)
            if at == -1:
                continue
            rest = q[at + len(word):]
            while True:
                stripped = CONNECTORS.sub("", rest, count=1)
                if stripped == rest:
                    break
                rest = stripped
            value = re.split(r"[?؟\n]", rest)[0].strip().strip("'\"«»“”.!،,")
            if value.lower() in EMPTY:
                value = ""
            if field == "answer":
                try:
                    return field, int(value)
                except ValueError:
                    pass
            return field, value
    return None, None


def answer_what_if(question, ctx, lang):
    workflow = ctx.workflow or default_workflow()
    original = ctx.item["trace"][0]["input"] if ctx.item and ctx.item.get("trace") else None
    base = copy.deepcopy(original) if isinstance(original, dict) else sample_lesson(workflow)
    field, value = parse_change(question, base)
    if field is None:
        return T["no_field"][lang], {"run": None, "lesson": None, "station": None}
    base[field] = value
    item = what_if(workflow, base)
    last = item["trace"][-1]
    station = station_label(last["type"], lang)
    if item.get("error"):
        outcome = T["wi_stop"][lang].format(station=station, status=item["status"], error=item["error"])
    elif item["status"] == "dry_run_preview":
        outcome = T["wi_pass"][lang].format(status=item["status"])
    else:
        outcome = T["wi_other"][lang].format(station=station, status=item["status"])
    name = FIELD_NAMES[lang].get(field, field)
    text = T["what_if"][lang].format(field=name, value=value, outcome=outcome, base=base.get("source_id", "?"))
    return text, {"run": "what-if dry run", "lesson": str(base.get("source_id")), "station": last["node"]}


# returns (kind, text, source). find(source_id) looks a lesson up in the saved runs.
def answer(question, lang, ctx, find=None):
    lang = pick_lang(question, lang)
    if is_action_request(question):
        return "refuse", T["refuse"][lang], source(ctx)

    # a lesson named in the question wins over the one on screen
    named = LESSON_ID.findall(question)
    if named and not (ctx.item and ctx.item.get("source_id") == named[0]):
        item = pick_item(ctx.report["items"], source_id=named[0]) if ctx.report else None
        if item:
            ctx.item = item
        else:
            found = find(named[0]) if find else None
            if not found:
                return "help", T["not_found"][lang].format(sid=named[0]), source(ctx)
            ctx = found

    q = question.lower()
    if WHAT_IF.search(q):
        text, src = answer_what_if(question, ctx, lang)
        return "what_if", text, src
    if WHY.search(q) or ((named or "this lesson" in q or "الدرس" in question) and ctx.item):
        if not ctx.item:
            return "help", T["need_lesson"][lang], source(ctx)
        text, node = explain_item(ctx.item, lang)
        return "why", text, source(ctx, ctx.item, node)
    station = station_in(question)
    if station and NODE_Q.search(q):
        label, text = STATIONS[station][lang]
        return "station", T["node"][lang].format(label=label, type=station, text=text), \
            {"run": None, "lesson": None, "station": station}
    if EXPLAIN_RUN.search(q):
        if not ctx.report and not ctx.item:
            return "help", T["need_run"][lang], source(ctx)
        if not ctx.report:
            text, node = explain_item(ctx.item, lang)
            return "why", text, source(ctx, ctx.item, node)
        return "run", explain_run(ctx, lang), source(ctx)
    if station:
        label, text = STATIONS[station][lang]
        return "station", T["node"][lang].format(label=label, type=station, text=text), \
            {"run": None, "lesson": None, "station": station}
    return "help", T["help"][lang], source(ctx)

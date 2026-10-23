# one question in, one answer out. read only: nothing here can approve, reject, save or publish.
import time

from . import fake, gemini, prompt
from .config import settings
from .context import Context, ContextError, find_lesson, from_dry_item, from_run

FRIENDLY = {
    "quota": {"en": "The model's free quota is used up right now (429), so I did not try again. Here is the plain answer:",
              "ar": "انتهت الحصة المجانية للنموذج الآن (429)، فلم أحاول مرة أخرى. هذه الإجابة البسيطة:"},
    "busy": {"en": "The model is busy (503). I waited 5 seconds and tried once more. Here is the plain answer:",
             "ar": "النموذج مشغول (503). انتظرت 5 ثوان وحاولت مرة واحدة أخرى. هذه الإجابة البسيطة:"},
    "failed": {"en": "The model did not answer. Here is the plain answer:",
               "ar": "لم يُجب النموذج. هذه الإجابة البسيطة:"},
    "empty": {"en": "The model gave an empty answer. Here is the plain answer:",
              "ar": "أعطى النموذج إجابة فارغة. هذه الإجابة البسيطة:"},
    "no_key": {"en": "Real mode is on (FAKE_MODEL=0) but GEMINI_API_KEY is empty, so no call was made. Here is the plain answer:",
               "ar": "الوضع الحقيقي مفعل (FAKE_MODEL=0) لكن GEMINI_API_KEY فارغ، فلم يتم أي اتصال. هذه الإجابة البسيطة:"},
    "claim": {"en": "The model's answer was not shown, because it said something was done. Masar can only read. Here is the plain answer:",
              "ar": "لم تُعرض إجابة النموذج لأنها قالت إن شيئا تم فعله. مسار يقرأ فقط. هذه الإجابة البسيطة:"},
}


def answer(question, lang, *, runs_dir, run_id=None, source_id=None, index=None, item=None, workflow=None,
           cfg=None, post=gemini.http_post, sleep=time.sleep):
    cfg = cfg or settings()
    if item is not None:
        ctx = from_dry_item(item, workflow)
    elif run_id:
        ctx = from_run(runs_dir, run_id, source_id=source_id, index=index)
    else:
        ctx = Context()

    def find(sid):
        try:
            return find_lesson(runs_dir, sid)
        except ContextError:
            return None

    kind, facts, src = fake.answer(question, lang, ctx, find=find)
    lang = fake.pick_lang(question, lang)
    # a refusal never goes to the model: there is nothing to explain, and it saves the quota
    if cfg["fake"] or kind == "refuse":
        return {"answer": facts, "source": {**src, "mode": "templates"}, "kind": kind}

    system, user = prompt.build(question, lang, ctx, facts)
    result = gemini.ask(system, user, cfg, post=post, sleep=sleep)
    text = result["text"]
    saved = bool(ctx.item and ctx.item.get("status") == "draft_saved")
    if text and gemini.claims_action(text, saved):
        result["error"], text = "claim", None
    if not text:
        return {"answer": f"{FRIENDLY[result['error']][lang]} {facts}",
                "source": {**src, "mode": f"templates ({result['error']})"}, "kind": kind, "calls": result["calls"]}
    return {"answer": text, "source": {**src, "mode": cfg["model"]}, "kind": kind, "calls": result["calls"]}

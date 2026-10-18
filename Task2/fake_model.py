# Fake model for FAKE_MODEL=1: same idea as Fake in the tests, but it
# finds a few known mistakes with simple rules, so any sentence works.
# No API key, no requests. Type "limit" to get a fake 429.

import re

from langchain_core.messages import AIMessage
from langchain_google_genai.chat_models import GoogleRateLimitError

from tutor import CheckResult, Mistake, RetryResult

# one rule per known mistake (small "i" is checked on its own)
RULES = [
    {
        "pattern": r"\bgoed\b", "correct": "went",
        "ar": "الفعل go فعل غير منتظم، وماضيه went وليس goed.",
        "hint": "تذكّر أن go فعل غير منتظم في الماضي.",
        "reason": "Past of go is irregular.",
        "explain": "معظم الأفعال في الإنجليزية تأخذ ed في الماضي، مثل play → played. "
                   "لكن بعض الأفعال غير منتظمة ولها شكل خاص يجب حفظه، و go واحد منها.",
        "examples": [("go", "went"), ("buy", "bought"), ("eat", "ate"), ("see", "saw")],
        "practice": ("Fill the gap: Last night we ___ (eat) pizza.", "ate"),
        "words": ["past", "goed", "went", "irregular"],
        "simple": 'بعض الأفعال لا تأخذ ed في الماضي. go يصبح went، احفظها مثل كلمة جديدة.',
        "more": [('take', 'took'), ('come', 'came'), ('write', 'wrote'), ('drink', 'drank'), ('swim', 'swam')],
    },
    {
        "pattern": r"\bbuyed\b", "correct": "bought",
        "ar": "الفعل buy فعل غير منتظم، وماضيه bought.",
        "hint": "الفعل buy غير منتظم، فلا نضيف إليه ed.",
        "reason": "Past of buy is irregular.",
        "explain": "الفعل buy من الأفعال غير المنتظمة، فلا نضيف إليه ed في الماضي. "
                   "ماضيه bought، ويجب حفظه.",
        "examples": [("buy", "bought"), ("bring", "brought"), ("think", "thought")],
        "practice": ("Fill the gap: Yesterday I ___ (buy) a new phone.", "bought"),
        "words": ["buyed", "bought"],
        "simple": 'buy في الماضي هو bought، بدون ed.',
        "more": [('catch', 'caught'), ('teach', 'taught'), ('fight', 'fought'), ('seek', 'sought')],
    },
    {
        "pattern": r"\bhe go\b", "correct": "he goes",
        "ar": "مع he وshe وit في المضارع البسيط نضيف s أو es إلى الفعل.",
        "hint": "انظر إلى الفاعل: he مفرد غائب.",
        "reason": "He/she/it needs -s.",
        "explain": "في المضارع البسيط، عندما يكون الفاعل he أو she أو it نضيف s أو es إلى الفعل.",
        "examples": [("I go", "he goes"), ("I play", "she plays"), ("I watch", "he watches")],
        "practice": ("Fill the gap: My sister ___ (work) in a bank.", "works"),
        "words": ["goes", "present"],
        "simple": 'مع he وshe وit أضف s إلى الفعل: he goes.',
        "more": [('I eat', 'she eats'), ('I study', 'he studies'), ('I fix', 'it fixes'), ('I watch', 'she watches')],
    },
    {
        "pattern": r"\bshe have\b", "correct": "she has",
        "ar": "مع he وshe وit نستخدم has وليس have.",
        "hint": "الفاعل she مفرد غائب، فما شكل have معه؟",
        "reason": "Use has with he/she/it.",
        "explain": "نستخدم have مع I وyou وwe وthey، ونستخدم has مع he وshe وit.",
        "examples": [("I have", "she has"), ("you have", "he has"), ("they have", "it has")],
        "practice": ("Fill the gap: He ___ (have) two brothers.", "has"),
        "words": ["has", "have"],
        "simple": 'مع he وshe وit قل has: she has.',
        "more": [('we have', 'he has'), ('I have a car', 'she has a car'), ('they have time', 'it has time')],
    },
    {
        "pattern": r"\ba apple\b", "correct": "an apple",
        "ar": "نستخدم an قبل الكلمة التي تبدأ بصوت متحرك مثل apple.",
        "hint": "انظر إلى الحرف الأول من الكلمة بعد أداة النكرة.",
        "reason": "Use an before a vowel sound.",
        "explain": "نستخدم an قبل الكلمة التي تبدأ بصوت متحرك (a, e, i, o, u)، "
                   "ونستخدم a قبل الصوت الساكن. المهم هو الصوت وليس الحرف.",
        "examples": [("a apple", "an apple"), ("a hour", "an hour"), ("an car", "a car")],
        "practice": ("Fill the gap: I ate ___ orange. (a / an)", "an"),
        "words": ["an", "a or an", "a/an", "article"],
        "simple": 'إذا بدأت الكلمة بصوت a أو e أو i أو o أو u قل an: an apple.',
        "more": [('a egg', 'an egg'), ('a umbrella', 'an umbrella'), ('an university', 'a university'), ('a honest man', 'an honest man')],
    },
    {
        "pattern": r"\bhe don't\b", "correct": "he doesn't",
        "ar": "مع he وshe وit نستخدم doesn't في النفي وليس don't.",
        "hint": "مع he نستخدم شكلًا آخر من do في النفي.",
        "reason": "Use doesn't with he/she/it.",
        "explain": "في نفي المضارع البسيط نستخدم don't مع I وyou وwe وthey، "
                   "ونستخدم doesn't مع he وshe وit، والفعل بعدها يبقى بدون s.",
        "examples": [("I don't", "he doesn't"), ("they don't", "she doesn't")],
        "practice": ("Fill the gap: She ___ (not like) coffee.", "doesn't like"),
        "words": ["doesn't", "don't", "negative"],
        "simple": "مع he وshe وit قل doesn't: he doesn't like.",
        "more": [("we don't", "it doesn't"), ("you don't know", "he doesn't know"), ("I don't play", "she doesn't play")],
    },
]

SMALL_I = {
    "pattern": None, "correct": "I",
    "ar": "الضمير I يُكتب دائمًا بحرف كبير.",
    "hint": "انتبه إلى طريقة كتابة الضمير I.",
    "reason": "Always write I as a capital.",
    "explain": "الضمير I بمعنى \"أنا\" يُكتب دائمًا بحرف كبير، حتى في وسط الجملة.",
    "examples": [("i am", "I am"), ("my friend and i", "my friend and I")],
    "practice": ("Fix it: my brother and i are friends.", "I"),
    "words": ["capital"],
    "simple": 'كلمة I بمعنى أنا تُكتب دائمًا كبيرة.',
    "more": [('i think', 'I think'), ('can i go?', 'can I go?'), ("i'm happy", "I'm happy")],
}
SMALL_I_RE = r"(?<![\w'])i(?![\w'])"

# warm when it is all correct, gentle when there are mistakes
REPLIES_OK = [
    "Great sentence! What did you do next?",
    "Very good, all correct! Can you tell me more?",
    "Lovely, no mistakes! What do you think about it?",
]
REPLIES_FIX = [
    "Nice try, just a small thing to fix. What happened after that?",
    "Good idea! Let's fix it together. Can you tell me more?",
    "Almost there! What did you do next?",
]


def key(text):
    return text.strip().strip('"').lower()


def cap(word, like):
    return word[0].upper() + word[1:] if like[0].isupper() else word


def find(sentence):
    # -> [(wrong, correct, rule)]
    found = []
    for rule in RULES:
        for m in re.finditer(rule["pattern"], sentence, re.IGNORECASE):
            found.append((m.group(0), cap(rule["correct"], m.group(0)), rule))
    for m in re.finditer(SMALL_I_RE, sentence):
        found.append(("i", "I", SMALL_I))
    return found


def fix_all(sentence):
    for rule in RULES:
        sentence = re.sub(rule["pattern"], lambda m: cap(rule["correct"], m.group(0)),
                          sentence, flags=re.IGNORECASE)
    return re.sub(SMALL_I_RE, "I", sentence)


def check_limit(text):
    if key(text) == "limit":
        raise GoogleRateLimitError("fake 429: daily limit reached")


class FakeChecker:
    def __init__(self):
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        sentence = messages[-1].content
        check_limit(sentence)
        errors, seen = [], set()
        for wrong, correct, rule in find(sentence):
            if key(wrong) not in seen:
                seen.add(key(wrong))
                errors.append(Mistake(wrong=wrong, correct=correct,
                                      explanation_ar=rule["ar"], reason_en=rule["reason"]))
        return CheckResult(
            has_errors=bool(errors),
            errors=errors,
            corrected=fix_all(sentence),
            reply=(REPLIES_FIX if errors else REPLIES_OK)[self.calls % 3],
        )


class FakeRetryChecker:
    def __init__(self):
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        text = messages[-1].content
        new_try = text.split("New try: ", 1)[1]
        check_limit(new_try)
        olds = re.findall(r'^- "(.*?)" -> "', text, re.MULTILINE)
        # a mistake is still wrong if the rules find it again in the new try
        hits = find(new_try)
        found = {key(w): rule["hint"] for w, _, rule in hits}
        still = [w for w in olds if key(w) in found]
        hint = found[key(still[0])] if still else ""
        # new mistakes in the whole new try
        old_keys = {key(w) for w in olds}
        new, seen = [], set()
        for wrong, correct, rule in hits:
            if key(wrong) not in old_keys and key(wrong) not in seen:
                seen.add(key(wrong))
                new.append(Mistake(wrong=wrong, correct=correct,
                                   explanation_ar=rule["ar"], reason_en=rule["reason"]))
        return RetryResult(still_wrong=still, hint=hint, new_errors=new, corrected=fix_all(new_try))


# the buttons Maher suggests after each kind of answer
AFTER_EXPLAIN = ["Simpler please", "More examples", "Test me"]
AFTER_PRACTICE = ["Give me a hint", "Show me the answer"]
AFTER_WRONG = ["Give me a hint", "Show me the answer", "Explain again"]
AFTER_DONE = ["Another one, please", "I'm done, thanks"]
GENERAL = ["Explain past simple", 'When do I use "an"?', "Test me"]


class FakeAsker:
    # answers Ask Maher questions from the same rules
    def __init__(self):
        self.calls = 0

    def invoke(self, messages):
        from ask import AskResult, Example  # here to avoid a circular import

        self.calls += 1
        text = messages[-1].content
        check_limit(text)
        low = text.lower()

        def say(answer, examples=(), practice="", passed=False, next_=AFTER_EXPLAIN):
            return AskResult(
                answer_ar=answer,
                examples=[Example(before=b, after=a) for b, a in examples],
                practice=practice,
                passed=passed,
                suggestions=list(next_),
            )

        def explain(rule):
            return say(rule["explain"], rule["examples"], rule["practice"][0],
                       next_=["Simpler please", "More examples", "Give me a hint"])

        def asks(*words):
            return any(w in low for w in words)

        # Practice it (My mistakes)
        m = re.search(r'The mistake: "(.*?)" -> ".*?"\. Give me one short practice', text)
        if m:
            hit = find(m.group(1))
            rule = hit[0][2] if hit else RULES[0]
            return say("حسنًا، جرّب هذا السؤال:", practice=rule["practice"][0], next_=AFTER_PRACTICE)

        last = next((m.content for m in reversed(messages[:-1]) if isinstance(m, AIMessage)), "")
        everything = RULES + [SMALL_I]
        # last practice question and last topic
        asked = next((r for r in everything if r["practice"][0] in last), None)
        topic = asked or next((r for r in everything
                               if r["explain"] in last or r["hint"] in last or r["simple"] in last or r["ar"] in last
                               or any(f"{b} -> {a}" in last for b, a in r["examples"] + r["more"])), None)

        if asks("show me the answer", "the answer") and asked:
            right = asked["practice"][1]
            return say(f"الإجابة: {right}. {asked['ar']} هل تريد سؤالًا آخر أم انتهينا؟", next_=AFTER_DONE)
        if asks("hint") and asked:
            return say(f"{asked['hint']} جرّب مرة أخرى:", practice=asked["practice"][0],
                       next_=["Show me the answer", "Explain again"])
        if asks("another one", "another question") and topic:
            rule = everything[(everything.index(topic) + 1) % len(everything)]
            return say("حسنًا، هذا سؤال جديد:", practice=rule["practice"][0], next_=AFTER_PRACTICE)
        if asks("explain again") and topic:
            return say(topic["explain"], topic["examples"], next_=AFTER_EXPLAIN)
        if asks("simpler", "simple", "don't understand", "أبسط", "ما فهمت"):
            if not topic:
                return say("عن أي قاعدة؟ اسألني عن قاعدة أولًا، ثم اطلب شرحًا أبسط.", next_=GENERAL)
            return say(topic["simple"], topic["examples"][:1], next_=["More examples", "Test me"])
        if asks("more examples", "another example", "أمثلة"):
            if not topic:
                return say("عن أي قاعدة؟ اسألني عن قاعدة أولًا، ثم اطلب أمثلة أكثر.", next_=GENERAL)
            return say("هذه أمثلة جديدة على نفس القاعدة:", topic["more"], next_=["Test me", "Simpler please"])
        if asks("test me", "quiz") and topic:
            return say("حسنًا، جرّب هذا السؤال:", practice=topic["practice"][0], next_=AFTER_PRACTICE)

        # an answer to the last practice question?
        if asked and "?" not in text and len(text) < 40:
            right = asked["practice"][1]
            # "I" must be a capital, the others don't care
            if right == "I":
                ok = re.search(r"(?<![\w'])I(?![\w'])", text) and not re.search(SMALL_I_RE, text)
            else:
                ok = right.lower() in low
            if ok:
                # right, but note other slips
                slips = [f"{w} ← {c}" for w, c, r in find(text) if r is not asked]
                if len(text.split()) >= 3 and text[0].islower():
                    slips.append("ابدأ الجملة بحرف كبير")
                note = f" ملاحظة صغيرة: {'، '.join(slips)}." if slips else ""
                return say(f"أحسنت! الإجابة صحيحة: {right}.{note} هل تريد سؤالًا آخر أم انتهينا؟",
                           passed=True, next_=AFTER_DONE)
            # wrong: hint + same test, no answer
            return say(f"ليس تمامًا. {asked['hint']} جرّب مرة أخرى:", practice=asked["practice"][0],
                       next_=AFTER_WRONG)

        # still fixing: hint only, examples could show the answer
        m = re.search(r'The mistake is in "(.*?)"', text)
        if m:
            hit = find(m.group(1))
            hint = hit[0][2]["hint"] if hit else "اقرأ جملتك مرة أخرى ببطء، وانتبه إلى هذه الكلمة."
            return say(f"{hint} حاول مرة أخرى، أنت قريب!", next_=["Simpler please"])

        # Ask Maher why
        m = re.search(r'"(.*?)" -> "', text)
        if m:
            hit = find(m.group(1))
            if hit:
                return explain(hit[0][2])

        if any(w in low for w in ["test", "quiz", "practice", "exercise"]):
            rule = RULES[self.calls % len(RULES)]
            return say("حسنًا، جرّب هذا السؤال:", practice=rule["practice"][0], next_=AFTER_PRACTICE)

        for rule in everything:
            # whole words only, so "an" doesn't match "and"
            if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", low) for w in rule["words"]):
                return explain(rule)

        return say(
            "سؤال جيد! في الوضع التجريبي أعرف قواعد قليلة فقط: الماضي (go → went)، "
            "و a / an، و has / have، و doesn't. اسألني عن واحدة منها.",
            next_=GENERAL,
        )

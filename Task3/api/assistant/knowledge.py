# what the stations and statuses mean, in both languages. used by the template answers.

STATIONS = {
    "validate_lesson": {
        "en": ("Validate", "checks that source_id, title, category, level, language and body are filled in, "
               "that the level is A1 to C2, and that the language is allowed. A lesson that fails here gets "
               "failed_validation and is never retried."),
        "ar": ("التحقق", "تفحص أن الحقول source_id و title و category و level و language و body ليست فارغة، "
               "وأن المستوى من A1 إلى C2، وأن اللغة مسموحة. الدرس الذي يفشل هنا يأخذ failed_validation "
               "ولا تُعاد المحاولة أبدا."),
    },
    "normalize_lesson": {
        "en": ("Normalize", "cleans the lesson without changing what it says: trims spaces, joins double spaces, "
               "writes the level in capitals and makes the slug."),
        "ar": ("التنظيف", "تنظف الدرس دون تغيير معناه: تحذف المسافات الزائدة، وتكتب المستوى بأحرف كبيرة، "
               "وتصنع الـ slug."),
    },
    "word_count": {
        "en": ("Count words", "counts the words in the body. The number goes into the report and the draft."),
        "ar": ("عد الكلمات", "تعد كلمات النص. يظهر العدد في التقرير وفي المسودة."),
    },
    "validate_question": {
        "en": ("Validate question", "checks that a question has exactly 4 options, none empty and none repeated, "
               "an answer from 0 to 3, a CEFR level and a topic."),
        "ar": ("التحقق من السؤال", "تفحص أن للسؤال 4 خيارات بالضبط، لا خيار فارغ ولا مكرر، وأن الجواب من 0 "
               "إلى 3، وأن هناك مستوى وموضوعا."),
    },
    "normalize_question": {
        "en": ("Normalize question", "keeps only the known fields of a question and trims them."),
        "ar": ("تنظيف السؤال", "تبقي الحقول المعروفة للسؤال فقط وتحذف المسافات الزائدة."),
    },
    "check_duplicate": {
        "en": ("Check duplicates", "looks for the same source_id in the saved drafts and earlier in the input "
               "(skipped_duplicate), and compares the cleaned title in English and Arabic. A title that looks "
               "the same is not skipped: it becomes possible_duplicate and waits for a person."),
        "ar": ("فحص التكرار", "تبحث عن نفس source_id في المسودات المحفوظة وفي ما سبق من المدخلات "
               "(skipped_duplicate)، وتقارن العنوان بعد تنظيفه بالعربية والإنجليزية. العنوان المشابه لا يُتخطى: "
               "يصبح possible_duplicate وينتظر شخصا."),
    },
    "manual_approval": {
        "en": ("Approval", "is the human gate. Without a reviewer name the lesson stops here as review_pending "
               "and waits in the Review Inbox. Nothing is saved until a person decides there."),
        "ar": ("الموافقة", "هي البوابة البشرية. بدون اسم مراجع يتوقف الدرس هنا بحالة review_pending وينتظر في "
               "صندوق المراجعة. لا يُحفظ شيء حتى يقرر شخص هناك."),
    },
    "save_draft": {
        "en": ("Save draft", "saves the lesson as a draft with the reviewer name and the time. Nothing is "
               "published. In a dry run it writes nothing (dry_run_preview)."),
        "ar": ("حفظ المسودة", "تحفظ الدرس كمسودة مع اسم المراجع والوقت. لا يُنشر شيء. في التشغيل التجريبي لا "
               "تكتب شيئا (dry_run_preview)."),
    },
    "log_result": {
        "en": ("Audit log", "marks the end of the line. The audit log gets one line for every lesson, also the "
               "ones that stopped early."),
        "ar": ("سجل التدقيق", "نهاية الخط. يأخذ سجل التدقيق سطرا لكل درس، حتى الدروس التي توقفت مبكرا."),
    },
}

# words people use for a station -> node type
STATION_WORDS = {
    "check_duplicate": ["duplicate", "dedup", "deduplicate", "check_duplicate", "التكرار", "مكرر"],
    "manual_approval": ["approval", "manual_approval", "human gate", "gate", "الموافقة", "البوابة"],
    "save_draft": ["save draft", "save_draft", "persist", "حفظ المسودة"],
    "word_count": ["word count", "count words", "word_count", "عد الكلمات"],
    "validate_question": ["validate_question", "validate question", "التحقق من السؤال"],
    "normalize_question": ["normalize_question", "normalize question", "تنظيف السؤال"],
    "validate_lesson": ["validate", "validation", "validate_lesson", "التحقق"],
    "normalize_lesson": ["normalize", "normalise", "normalize_lesson", "clean", "التنظيف"],
    "log_result": ["audit", "log_result", "سجل التدقيق"],
}

STATUS = {
    "failed_validation": {"en": "the lesson data is wrong, so it stopped. It is never retried.",
                          "ar": "بيانات الدرس خاطئة، فتوقف. لا تُعاد المحاولة أبدا."},
    "failed_error": {"en": "a station broke. This is a bug in a station, not bad input.",
                     "ar": "تعطلت محطة. هذا خطأ في المحطة، وليس في المدخلات."},
    "review_pending": {"en": "it waits in the Review Inbox for a person. Nothing is saved until someone approves it there.",
                       "ar": "ينتظر في صندوق المراجعة. لا يُحفظ شيء حتى يوافق عليه شخص هناك."},
    "possible_duplicate": {"en": "its title looks like {dup}. A person must approve this one lesson by name in the Review Inbox.",
                           "ar": "عنوانه يشبه {dup}. يجب أن يوافق شخص على هذا الدرس بالاسم في صندوق المراجعة."},
    "skipped_duplicate": {"en": "the same source_id is already saved or came earlier in the input, so it was skipped.",
                          "ar": "نفس source_id محفوظ من قبل أو جاء قبله في المدخلات، فتم تخطيه."},
    "draft_saved": {"en": "it was saved as a draft. It is not published.",
                    "ar": "حُفظ كمسودة. وهو غير منشور."},
    "dry_run_preview": {"en": "it passed every station in a dry run. Nothing was written.",
                        "ar": "مر على كل المحطات في تشغيل تجريبي. لم يُكتب أي شيء."},
    "rejected": {"en": "a reviewer rejected it. Nothing was saved.",
                 "ar": "رفضه مراجع. لم يُحفظ أي شيء."},
    "complete": {"en": "it went through the whole line.", "ar": "مر على الخط كله."},
}

# in a dry run nothing is saved, so a lesson that stopped at approval is not in the inbox
STATUS_DRY = {
    "review_pending": {"en": "this was a dry run, so nothing was saved and it is not in the Review Inbox. "
                             "In a real run it would wait there for a person.",
                       "ar": "كان هذا تشغيلا تجريبيا، فلم يُحفظ شيء والدرس ليس في صندوق المراجعة. "
                             "في تشغيل حقيقي سينتظر هناك شخصا."},
    "possible_duplicate": {"en": "its title looks like {dup}. This was a dry run, so nothing was saved and it is "
                                 "not in the Review Inbox. In a real run a person would have to approve this one "
                                 "lesson by name.",
                           "ar": "عنوانه يشبه {dup}. كان هذا تشغيلا تجريبيا، فلم يُحفظ شيء والدرس ليس في صندوق "
                                 "المراجعة. في تشغيل حقيقي يجب أن يوافق شخص على هذا الدرس بالاسم."},
}

MODES = {"dry-run": {"en": "dry run", "ar": "تشغيل تجريبي"},
         "review": {"en": "review run", "ar": "تشغيل للمراجعة"},
         "approved": {"en": "approved run", "ar": "تشغيل بموافقة"}}


def station_label(node_type, lang):
    return STATIONS.get(node_type, {}).get(lang, (node_type, ""))[0]

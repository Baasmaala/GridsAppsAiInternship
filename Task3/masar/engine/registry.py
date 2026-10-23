from .nodes.flow_nodes import check_duplicate, log_result, manual_approval, save_draft
from .nodes.lesson_nodes import normalize_lesson, validate_lesson, word_count
from .nodes.question_nodes import normalize_question, validate_question

# the only node types the engine runs. a workflow file can only pick from here.
NODES = {
    "validate_lesson": validate_lesson,
    "normalize_lesson": normalize_lesson,
    "word_count": word_count,
    "validate_question": validate_question,
    "normalize_question": normalize_question,
    "check_duplicate": check_duplicate,
    "manual_approval": manual_approval,
    "save_draft": save_draft,
    "log_result": log_result,
}

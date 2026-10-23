import { checkDuplicate, logResult, manualApproval, saveDraft } from './nodes/flow_nodes.mjs';
import { normalizeLesson, validateLesson, wordCount } from './nodes/lesson_nodes.mjs';

// the only node types the engine runs. a workflow file can only pick from here.
export const NODES = {
  validate_lesson: validateLesson,
  normalize_lesson: normalizeLesson,
  word_count: wordCount,
  check_duplicate: checkDuplicate,
  manual_approval: manualApproval,
  save_draft: saveDraft,
  log_result: logResult,
};

import { step } from '../context.mjs';
import { ValidationError } from '../errors.mjs';
import { LEVELS, isObject, isText, oneLine } from './lesson_nodes.mjs';

const FIELDS = ['source_id', 'question', 'options', 'answer', 'level', 'topic'];
const TEXT_FIELDS = new Set(['source_id', 'question', 'level', 'topic']);

// like python repr for the answer value
const show = v => (v === true ? 'True' : v === false ? 'False' : typeof v === 'string' ? `'${v}'` : JSON.stringify(v));

export function validateQuestion(data, run) {
  if (!isObject(data)) throw new ValidationError('Question must be an object');
  const missing = FIELDS.filter(k => (TEXT_FIELDS.has(k) ? !isText(data[k]) : data[k] == null));
  if (missing.length) throw new ValidationError(`Missing/empty field: ${missing.join(', ')}`);

  const problems = [];
  const options = data.options;
  if (!Array.isArray(options) || options.length !== 4) {
    const got = Array.isArray(options) ? options.length : typeof options;
    problems.push(`options must be a list of exactly 4 answers (got ${got})`);
  } else {
    const empty = options.map((o, i) => (isText(o) ? null : String(i + 1))).filter(Boolean);
    if (empty.length) {
      problems.push(`option ${empty.join(', ')} is empty`);
    } else {
      const seen = options.map(o => oneLine(o).toLowerCase());
      const repeated = [...new Set(seen.filter(o => seen.indexOf(o) !== seen.lastIndexOf(o)))].sort();
      if (repeated.length) problems.push(`options repeat: ${repeated.join(', ')}`);
    }
  }
  const answer = data.answer;
  if (!Number.isInteger(answer) || answer < 0 || answer > 3) {
    problems.push(`answer must be the number of the right option, 0 to 3 (got ${show(answer)})`);
  }
  if (!LEVELS.includes(data.level.trim().toUpperCase())) {
    problems.push(`Invalid CEFR level '${data.level}' (use ${LEVELS.join(', ')})`);
  }
  if (problems.length) throw new ValidationError(problems.join('; '));
  return step(data);
}

export function normalizeQuestion(data, run) {
  // keep only the known fields, trimmed
  return step({
    source_id: data.source_id.trim(),
    question: oneLine(data.question),
    options: data.options.map(oneLine),
    answer: data.answer,
    level: data.level.trim().toUpperCase(),
    topic: oneLine(data.topic),
    status: 'draft',
  });
}

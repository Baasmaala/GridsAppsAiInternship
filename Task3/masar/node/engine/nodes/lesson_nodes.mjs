import { step } from '../context.mjs';
import { ValidationError } from '../errors.mjs';

export const REQUIRED = ['source_id', 'title', 'category', 'level', 'language', 'body'];
export const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

export const isText = v => typeof v === 'string' && v.trim() !== '';
export const isObject = v => v !== null && typeof v === 'object' && !Array.isArray(v);
export const oneLine = text => text.replace(/\s+/g, ' ').trim();

// keep letters, marks and digits from any language, the rest becomes "-"
export function slugify(text) {
  return text.toLowerCase().split(/[^\p{L}\p{M}\p{N}]+/u).filter(Boolean).join('-');
}

export function validateLesson(data, run) {
  if (!isObject(data)) throw new ValidationError('Lesson must be an object');
  const missing = REQUIRED.filter(k => !isText(data[k]));
  if (missing.length) throw new ValidationError(`Missing/empty field: ${missing.join(', ')}`);

  const problems = [];
  if (!LEVELS.includes(data.level.trim().toUpperCase())) {
    problems.push(`Invalid CEFR level '${data.level}' (use ${LEVELS.join(', ')})`);
  }
  if (!run.allowedLanguages.includes(data.language.trim().toLowerCase())) {
    problems.push(`Language '${data.language}' is not allowed ` +
      `(allowed: ${run.allowedLanguages.join(', ')})`);
  }
  const tags = data.tags;
  if (tags != null && !(Array.isArray(tags) && tags.every(t => typeof t === 'string'))) {
    problems.push('tags must be a list of strings');
  }
  if (problems.length) throw new ValidationError(problems.join('; '));
  return step(data);
}

export function cleanTags(tags) {
  const out = [];
  for (const raw of tags) {
    const tag = oneLine(raw).toLowerCase();
    if (tag && !out.includes(tag)) out.push(tag);
  }
  return out;
}

export function normalizeLesson(data, run) {
  const d = Object.fromEntries(REQUIRED.map(k => [k, data[k].trim()]));
  // body keeps its own spacing and lines, only trimmed
  d.title = oneLine(d.title);
  d.category = oneLine(d.category);
  d.level = d.level.toUpperCase();
  d.language = d.language.toLowerCase();
  if (data.tags != null) d.tags = cleanTags(data.tags);
  d.slug = slugify(d.title);
  d.status = 'draft';
  if (!d.slug) throw new ValidationError('Cannot generate slug from title');
  return step(d);
}

export function wordCount(data, run) {
  const body = isObject(data) ? data.body : undefined;
  if (typeof body !== 'string') throw new ValidationError('word_count needs a text body');
  return step({ ...data, word_count: body.split(/\s+/).filter(Boolean).length });
}

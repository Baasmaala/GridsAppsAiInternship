import { createHash } from 'node:crypto';

import { isObject, isText } from './nodes/lesson_nodes.mjs';

const TASHKEEL = /[ؐ-ًؚ-ٰٟۖ-ۭـ]/g;  // + tatweel
const LETTERS = { 'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ة': 'ه', 'ى': 'ي' };

// only for comparing. the stored text is never changed.
export function cleanForCompare(text) {
  const t = text.normalize('NFKC').replace(TASHKEEL, '').replace(/[أإآٱةى]/g, c => LETTERS[c]).toLowerCase();
  return t.replace(/[\p{P}\p{S}\p{Z}\p{C}]/gu, ' ').split(' ').filter(Boolean).join(' ');
}

export function fingerprint(text) {
  if (typeof text !== 'string') return null;
  const cleaned = cleanForCompare(text);
  return cleaned ? createHash('sha256').update(cleaned, 'utf8').digest('hex') : null;
}

// lessons have a title, questions have a question
export function printSource(data) {
  if (!isObject(data)) return null;
  for (const key of ['title', 'question']) if (isText(data[key])) return data[key];
  return null;
}

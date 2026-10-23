import { describe, expect, test } from 'vitest';

import { ar, dirFor, en, format } from '../i18n/strings';

describe('english and arabic', () => {
  test('same keys, none empty', () => {
    expect(Object.keys(ar).sort()).toEqual(Object.keys(en).sort());
    for (const [key, text] of Object.entries(ar)) expect(text.trim(), key).not.toBe('');
  });

  test('the same {placeholders} in both', () => {
    const holes = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort();
    for (const key of Object.keys(en) as (keyof typeof en)[]) expect(holes(ar[key]), key).toEqual(holes(en[key]));
  });

  test('every node type has a plain label, a job and a stop rule', () => {
    // the allowlist in masar/engine/registry.py, plus the start station
    const types = ['trigger', 'validate_lesson', 'normalize_lesson', 'word_count', 'validate_question',
      'normalize_question', 'check_duplicate', 'manual_approval', 'save_draft', 'log_result'];
    for (const type of types) {
      for (const part of ['label', 'checks', 'stops']) expect(`node.${type}.${part}` in en, `${type} ${part}`).toBe(true);
    }
  });

  test('language names', () => {
    expect([en['lang.name.en'], ar['lang.name.en']]).toEqual(['English', 'الإنجليزية']);
    expect(format(ar['wf.language'], { list: ar['lang.name.en'] })).toBe('اللغة: الإنجليزية');
  });

  test('arabic is right to left', () => {
    expect(dirFor('ar')).toBe('rtl');
    expect(dirFor('en')).toBe('ltr');
  });

  test('the switch shows the other language', () => {
    expect(en['lang.switch']).toBe('العربية');
    expect(ar['lang.switch']).toBe('English');
  });

  test('format fills placeholders', () => {
    expect(format('{n} stations', { n: 7 })).toBe('7 stations');
    expect(format('{n} stations')).toBe('{n} stations');
  });
});

export type DiffRow = { key: string; before: unknown; after: unknown; change: 'same' | 'added' | 'removed' | 'changed' };

const isObject = (v: unknown): v is Record<string, unknown> =>
  v !== null && typeof v === 'object' && !Array.isArray(v);

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

// field by field, keys in the order they first show up (before first, then new ones)
export function diffFields(before: unknown, after: unknown): DiffRow[] | null {
  if (!isObject(before) || (after !== undefined && !isObject(after))) return null;
  const a = before;
  const b = after ?? {};
  const keys = [...Object.keys(a), ...Object.keys(b).filter(k => !(k in a))];
  return keys.map(key => {
    const inA = key in a;
    const inB = key in b;
    const change = !inA ? 'added' : !inB ? 'removed' : same(a[key], b[key]) ? 'same' : 'changed';
    return { key, before: a[key], after: b[key], change };
  });
}

export function show(value: unknown): string {
  if (value === undefined) return '';
  return typeof value === 'string' ? value : JSON.stringify(value);
}

// fields for people who know the engine. hidden until "Show details" is on.
export const TECH_FIELDS = ['source_id', 'slug', 'status', 'possible_duplicate_of'];

export function plainRows(rows: DiffRow[]): DiffRow[] {
  return rows.filter(r => !TECH_FIELDS.includes(r.key));
}

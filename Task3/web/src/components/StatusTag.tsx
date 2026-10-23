import type { ReactNode } from 'react';

import { useLang } from '../i18n/lang';
import { statusLook } from '../lib/status';

// color + a short word, and the real status in mono for people who know the engine
export function StatusTag({ status, raw = false }: { status: string; raw?: boolean }) {
  const { t } = useLang();
  const look = statusLook(status);
  return (
    <span className="tag">
      <span className="tag-dot" style={{ background: look.color }} />
      {look.word ? t(look.word) : status}
      {raw && <span className="mono muted">{status}</span>}
    </span>
  );
}

// the same look for anything that is not an engine status
export function Badge({ color, children }: { color: string; children: ReactNode }) {
  return (
    <span className="tag">
      <span className="tag-dot" style={{ background: color }} />
      {children}
    </span>
  );
}

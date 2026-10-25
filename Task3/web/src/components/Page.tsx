import type { ReactNode } from 'react';

import type { ApiError } from '../api/client';
import { useLang } from '../i18n/lang';
import { DetailsSwitch } from '../lib/details';

export function Page({ title, intro, children, actions }: {
  title: string; intro?: string; children: ReactNode; actions?: ReactNode;
}) {
  return (
    <main className="wrap page">
      <div className="page-top">
        <div className="page-head">
          <h1>{title}</h1>
          {intro && <p className="muted">{intro}</p>}
        </div>
        <div className="page-actions">{actions}<DetailsSwitch /></div>
      </div>
      {children}
    </main>
  );
}

// no connection gets the start command, other errors get their message
export function ErrorNote({ error }: { error: ApiError | null }) {
  const { t } = useLang();
  if (!error) return null;
  return (
    <div className="card notice is-error" role="alert">
      {error.status === 0 ? t('common.noApi') : t('common.error', { msg: error.message })}
      {error.errors.length > 0 && (
        <ul className="errors">{error.errors.map(e => <li key={e}>{e}</li>)}</ul>
      )}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="card notice">{children}</div>;
}

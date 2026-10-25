import { useState } from 'react';

import { api, ApiError, type Challenge } from '../api/client';
import { Icon } from '../components/Icon';
import { ErrorNote, Page } from '../components/Page';
import { Badge } from '../components/StatusTag';
import { useLang } from '../i18n/lang';
import type { Key } from '../i18n/strings';

const NUMBERS = [1, 2, 3, 4, 5] as const;

export function LabPage() {
  const { t } = useLang();
  const [results, setResults] = useState<Challenge[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  async function runAll() {
    setBusy(true);
    setError(null);
    try {
      setResults((await api.challenges()).results);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  }

  const passed = results?.filter(r => r.passed).length ?? 0;
  return (
    <Page title={t('lab.title')}
      actions={<button type="button" className="btn btn-primary" onClick={runAll} disabled={busy}>
        {busy ? t('run.running') : t('lab.runAll')}</button>}>
      <ErrorNote error={error} />
      {results && (
        <div className={`card notice score ${passed === results.length ? 'is-ok' : 'is-error'}`} role="status">
          <Icon name={passed === results.length ? 'check' : 'cross'} />{' '}
          {t('lab.score', { n: passed, total: results.length })}
        </div>
      )}
      <div className="lab">
        {NUMBERS.map(n => {
          const r = results?.find(x => x.number === n);
          const k = (part: string) => `lab.${n}.${part}` as Key;
          return (
            <article key={n} className={`card pad challenge ${r ? (r.passed ? 'is-ok' : 'is-error') : ''}`}>
              <div className="challenge-top">
                <span className="challenge-n mono">{n}</span>
                <h2>{t(k('name'))}</h2>
                {r && <Badge color={r.passed ? 'var(--ok)' : 'var(--fail)'}>{r.passed ? t('lab.pass') : t('lab.fail')}</Badge>}
              </div>
              <dl>
                <dt>{t('lab.what')}</dt><dd>{t(k('what'))}</dd>
                <dt>{t('lab.expect')}</dt><dd>{t(k('expect'))}</dd>
                {r && (<><dt>{t('lab.got')}</dt><dd className="mono">{r.got}</dd></>)}
              </dl>
            </article>
          );
        })}
      </div>
    </Page>
  );
}

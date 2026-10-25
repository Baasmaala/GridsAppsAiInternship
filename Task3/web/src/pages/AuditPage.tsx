import { useState } from 'react';

import { api, ApiError, type Verify } from '../api/client';
import { Icon } from '../components/Icon';
import { Empty, ErrorNote, Page } from '../components/Page';
import { StatusTag } from '../components/StatusTag';
import { useLang } from '../i18n/lang';
import { useDetails } from '../lib/details';
import { formatTime } from '../lib/time';
import { useLoad } from '../lib/useLoad';

export function AuditPage() {
  const { t, lang } = useLang();
  const details = useDetails();
  const lines = useLoad(() => api.audit());
  const [verify, setVerify] = useState<Verify | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  async function check() {
    setError(null);
    try {
      lines.reload();
      setVerify(await api.verify());
    } catch (e) {
      setError(e as ApiError);
    }
  }

  // before the broken line: fine. the broken line: red. after it: not checked.
  const mark = (seq: number) => {
    if (!verify) return null;
    if (verify.ok || (verify.broken_line ?? 0) > seq) return 'ok';
    return verify.broken_line === seq ? 'broken' : 'unchecked';
  };
  const cut = verify && !verify.ok && (verify.broken_line ?? 0) > verify.lines;
  const event = (e: string) => (e === 'run' || e === 'approve' || e === 'reject' ? t(`event.${e}`) : e);

  return (
    <Page title={t('au.title')} intro={t('au.intro')}
      actions={<button type="button" className="btn btn-primary" onClick={check}>{t('au.verify')}</button>}>
      <ErrorNote error={lines.error ?? error} />

      {verify && (
        <div className={`card notice ${verify.ok ? 'is-ok' : 'is-error'}`} role="status">
          <Icon name={verify.ok ? 'check' : 'cross'} />{' '}
          {verify.ok ? t('au.ok', { n: verify.lines })
            : cut ? t('au.cut', { n: verify.lines, reason: verify.reason ?? '' })
              : t('au.broken', { n: verify.broken_line ?? 0, reason: verify.reason ?? '' })}
        </div>
      )}

      {lines.data?.length === 0 && <Empty>{t('au.empty')}</Empty>}
      {lines.data && lines.data.length > 0 && (
        <section className={`card audit${details ? '' : ' no-hash'}`}>
          <div className="audit-row audit-head" role="row">
            <span>{t('au.seq')}</span><span>{t('au.time')}</span><span>{t('au.event')}</span>
            <span>{t('au.lesson')}</span><span>{t('au.status')}</span><span>{t('au.reviewer')}</span>
            <span>{t('au.reason')}</span>{details && <span>{t('au.hash')}</span>}
          </div>
          {lines.data.map(line => {
            const m = mark(line.seq);
            return (
              <div key={line.seq} className={`audit-row ${m ? `is-${m}` : ''}`} role="row">
                <span className="mono">
                  {m === 'ok' && <Icon name="check" size={14} />}
                  {m === 'broken' && <Icon name="cross" size={14} />} {line.seq}
                </span>
                <span className="mono muted">{formatTime(line.time, lang)}</span>
                <span>{event(line.event)}</span>
                <span className="mono">{String(line.source_id)}</span>
                <span>{details ? <span className="mono">{line.status}</span> : <StatusTag status={line.status} />}</span>
                <span>{line.reviewer ?? ''}</span>
                <span dir="auto">{line.reason ?? ''}</span>
                {details && <span className="mono muted" title={line.hash}>{line.hash.slice(0, 10)}</span>}
              </div>
            );
          })}
          {cut && <div className="audit-cut"><Icon name="cross" /> {verify?.reason}</div>}
        </section>
      )}
    </Page>
  );
}

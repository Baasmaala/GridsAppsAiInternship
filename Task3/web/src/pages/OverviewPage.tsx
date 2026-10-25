import { useState } from 'react';

import { api, ApiError } from '../api/client';
import { Icon } from '../components/Icon';
import { ErrorNote, Page } from '../components/Page';
import { Badge, StatusTag } from '../components/StatusTag';
import { useLang } from '../i18n/lang';
import { overviewCounts } from '../lib/counts';
import { useDetails } from '../lib/details';
import { modeName, workflowName } from '../lib/names';
import { link } from '../lib/route';
import { formatTime, shortId } from '../lib/time';
import { useLoad } from '../lib/useLoad';

export function OverviewPage() {
  const { t, lang } = useLang();
  const details = useDetails();
  const data = useLoad(async () => {
    const [runs, reviews, drafts, verify] = await Promise.all([api.runs(), api.reviews(), api.drafts(), api.verify()]);
    return { runs, counts: overviewCounts(runs, reviews, drafts.length), verify };
  });

  const tiles = data.data ? [
    { label: t('ov.drafts'), n: data.data.counts.drafts, color: 'var(--ok)', href: link('drafts') },
    { label: t('ov.waiting'), n: data.data.counts.waiting, color: 'var(--wait)', href: link('inbox') },
    { label: t('ov.lookalike'), n: data.data.counts.lookalike, color: 'var(--wait)', href: link('inbox') },
    { label: t('ov.failed'), n: data.data.counts.failed, color: 'var(--fail)', href: link('run') },
    { label: t('ov.skipped'), n: data.data.counts.skipped, color: 'var(--skip)', href: link('run') },
  ] : [];

  return (
    <Page title={t('ov.title')} intro={t('ov.intro')}>
      <ErrorNote error={data.error} />
      <StartHere />
      {data.data && (
        <>
          <div className="tiles">
            {tiles.map(tile => (
              <a key={tile.label} className="card tile" href={tile.href}>
                <span className="tile-n">{tile.n}</span>
                <span className="tag"><span className="tag-dot" style={{ background: tile.color }} />{tile.label}</span>
              </a>
            ))}
          </div>

          <div className="two-col">
            <section className="card">
              <h2 className="card-title">{t('ov.lastRuns')}</h2>
              {data.data.runs.length === 0 ? <p className="notice">{t('ov.noRuns')}</p> : (
                <ul className="rows">
                  {[...data.data.runs].reverse().slice(0, 5).map(r => (
                    <li key={r.run_id} className="row">
                      <div className="row-main">
                        <span>{workflowName(r.workflow_id, t)} · {modeName(r.mode, t)}</span>
                        <span className="muted">{formatTime(r.created_at, lang)}{details && <span className="mono"> {shortId(r.run_id)}</span>}</span>
                      </div>
                      <div className="row-tags">
                        {Object.entries(r.summary).map(([s, n]) => (
                          <span key={s} className="count-tag"><StatusTag status={s} /> {n}</span>
                        ))}
                      </div>
                      <a className="row-link" href={link('replay', { run: r.run_id })}>
                        {t('run.toReplay')} <Icon name="arrow" size={14} />
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <div className="stack">
              <section className="card pad">
                <h2 className="card-title flush">{t('ov.audit')}</h2>
                <p>{data.data.verify.ok ? (
                  data.data.verify.lines === 0
                    ? <Badge color="var(--skip)">{t('ov.auditEmpty')}</Badge>
                    : <Badge color="var(--ok)">{t('ov.auditOk', { n: data.data.verify.lines })}</Badge>
                ) : (
                  <Badge color="var(--fail)">{t('ov.auditBroken', { n: data.data.verify.broken_line ?? 0 })}</Badge>
                )}</p>
                <p><a className="row-link" href={link('audit')}>{t('nav.audit')} <Icon name="arrow" size={14} /></a></p>
              </section>
              <ResetCard onDone={data.reload} />
            </div>
          </div>
        </>
      )}
    </Page>
  );
}

function StartHere() {
  const { t } = useLang();
  const steps = [
    { text: t('start.1'), href: link('run') },
    { text: t('start.2'), href: link('inbox') },
    { text: t('start.3'), href: link('drafts') },
  ];
  return (
    <section className="card pad start-here" aria-labelledby="start-title">
      <h2 id="start-title" className="card-title flush">{t('start.title')}</h2>
      <ol className="start-steps">
        {steps.map((s, i) => (
          <li key={i}>
            <span className="start-n">{i + 1}</span>
            <a href={s.href}>{s.text}</a>
          </li>
        ))}
      </ol>
    </section>
  );
}

// two steps on purpose: the first click only asks
function ResetCard({ onDone }: { onDone: () => void }) {
  const { t } = useLang();
  const [asking, setAsking] = useState(false);
  const [seed, setSeed] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  async function reset() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.reset(seed);
      setMessage(r.seeded ? t('ov.resetSeeded') : t('ov.resetDone'));
      setAsking(false);
      onDone();
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card pad">
      <h2 className="card-title flush">{t('ov.reset')}</h2>
      <p className="muted">{t('ov.resetIntro')}</p>
      {asking ? (
        <>
          <label className="check">
            <input type="checkbox" checked={seed} onChange={e => setSeed(e.target.checked)} />
            {t('ov.resetSeed')}
          </label>
          <div className="buttons">
            <button type="button" className="btn btn-danger" onClick={reset} disabled={busy}>{t('ov.resetConfirm')}</button>
            <button type="button" className="btn" onClick={() => setAsking(false)} disabled={busy}>{t('ov.cancel')}</button>
          </div>
        </>
      ) : (
        <div className="buttons">
          <button type="button" className="btn" onClick={() => { setMessage(null); setAsking(true); }}>{t('ov.reset')}</button>
        </div>
      )}
      {message && <p className="result-line"><Icon name="check" /> {message}</p>}
      <ErrorNote error={error} />
    </section>
  );
}

import { useEffect, useState } from 'react';

import { api, type Item, type Report, type TraceEntry } from '../api/client';
import { DataDiff } from '../components/DataDiff';
import { Icon } from '../components/Icon';
import { Empty, ErrorNote, Page } from '../components/Page';
import { Badge, StatusTag } from '../components/StatusTag';
import { useLang } from '../i18n/lang';
import { useDetails } from '../lib/details';
import { useLastRun } from '../lib/lastRun';
import { itemTitle, modeName, stationName, workflowName } from '../lib/names';
import { link } from '../lib/route';
import { skipReason } from '../lib/skip';
import { statusLook } from '../lib/status';
import { formatTime, shortId } from '../lib/time';
import { useLoad } from '../lib/useLoad';

const DRY = 'dry';

function resultColor(entry: TraceEntry): string {
  if (entry.result === 'error') return 'var(--fail)';
  if (entry.result === 'stop') return statusLook(entry.status ?? '').color;
  return 'var(--ok)';
}

export function ReplayPage({ params }: { params: URLSearchParams }) {
  const { t, lang } = useLang();
  const details = useDetails();
  const { last } = useLastRun();
  const runs = useLoad(() => api.runs());

  const newest = runs.data?.length ? runs.data[runs.data.length - 1].run_id : null;
  const runId = params.get('run') ?? (last ? DRY : newest);
  const index = Number(params.get('i') ?? '0') || 0;

  const saved = useLoad<Report | null>(
    () => (runId && runId !== DRY ? api.runDetail(runId).then(d => d.report) : Promise.resolve(null)), [runId]);
  const report = runId === DRY ? last?.report ?? null : saved.data;
  const item = report?.items[index] ?? null;

  const [step, setStep] = useState(0);
  useEffect(() => setStep(0), [runId, index]);

  const go = (run: string, i: number) => { window.location.hash = link('replay', { run, i: String(i) }); };

  const noRuns = !last && runs.data?.length === 0;
  const skip = item ? skipReason(item) : null;
  const plainOption = (it: Item) => {
    const word = statusLook(it.status).word;
    return `${itemTitle(it)} (${word ? t(word) : it.status})`;
  };
  const entry = item?.trace[Math.min(step, item.trace.length - 1)];

  return (
    <Page title={t('rp.title')}>
      <ErrorNote error={runs.error ?? saved.error} />
      {noRuns && <Empty>{t('rp.noRuns')}</Empty>}

      {!noRuns && (
        <section className="card pad form">
          <div className="form-grid">
            <label className="field">
              <span>{t('rp.run')}</span>
              <select value={runId ?? ''} onChange={e => go(e.target.value, 0)}>
                {last && <option value={DRY}>{t('rp.lastDry')}</option>}
                {[...(runs.data ?? [])].reverse().map(r => (
                  <option key={r.run_id} value={r.run_id}>
                    {[formatTime(r.created_at, lang), workflowName(r.workflow_id, t), modeName(r.mode, t)].join(t('common.listSep'))}
                    {details && ` (${shortId(r.run_id)})`}
                  </option>
                ))}
              </select>
            </label>
            {report && (
              <label className="field">
                <span>{t('rp.lesson')}</span>
                <select value={index} onChange={e => go(runId ?? DRY, Number(e.target.value))}>
                  {report.items.map((it, i) => (
                    <option key={i} value={i}>{details ? `${String(it.source_id)} (${it.status})` : plainOption(it)}</option>
                  ))}
                </select>
              </label>
            )}
          </div>
        </section>
      )}

      {item && entry && (
        <section className="card">
          <div className="meta">
            {details ? <h2 className="mono-title">{String(item.source_id)}</h2> : <h2 dir="auto">{itemTitle(item)}</h2>}
            <StatusTag status={item.status} raw={details} />
            {skip && <span className="muted">{t(skip)}</span>}
            {item.word_count !== undefined && <span className="muted">{t('ib.words', { n: item.word_count })}</span>}
          </div>

          <div className="pad stepper">
            <ol className="steps">
              {item.trace.map((e, i) => (
                <li key={i}>
                  <button type="button" className="step-tab" aria-current={i === step ? 'step' : undefined}
                    onClick={() => setStep(i)}>
                    <span className="tag-dot" style={{ background: resultColor(e) }} />
                    {stationName(e.type, e.node, t)}
                  </button>
                </li>
              ))}
            </ol>
            <div className="slider-row">
              <button type="button" className="btn" onClick={() => setStep(s => Math.max(0, s - 1))} disabled={step === 0}>
                <span className="flip-back"><Icon name="arrow" size={14} /></span> {t('rp.prev')}
              </button>
              <input type="range" min={0} max={item.trace.length - 1} value={step}
                onChange={e => setStep(Number(e.target.value))}
                aria-label={t('rp.step', { n: step + 1, total: item.trace.length })} />
              <button type="button" className="btn" onClick={() => setStep(s => Math.min(item.trace.length - 1, s + 1))}
                disabled={step >= item.trace.length - 1}>
                {t('rp.next')} <Icon name="arrow" size={14} />
              </button>
              <span className="muted step-count">{t('rp.step', { n: step + 1, total: item.trace.length })}</span>
            </div>
          </div>

          <div className="detail">
            <div className="step-head">
              <h3>{stationName(entry.type, entry.node, t)}</h3>
              {details && <span className="station-type">{entry.node} · {entry.type}</span>}
              <Badge color={resultColor(entry)}>{t(`rp.result.${entry.result}`)}</Badge>
              {entry.status && <StatusTag status={entry.status} raw={details} />}
              {details && <span className="muted mono">{t('rp.ms', { ms: entry.ms })}</span>}
            </div>
            {entry.note && <p dir="auto">{entry.note}</p>}
            {entry.error && <p className="error-text" dir="auto"><Icon name="cross" /> {entry.error}</p>}
            {entry.attempts && (
              <div>
                <span className="diff-head">{t('rp.attempts')}</span>
                <ul className="plain">
                  {entry.attempts.map(a => (
                    <li key={a.attempt} className="mono">
                      {t('rp.attempt', { n: a.attempt, what: a.error ? `${a.error}${a.wait_s ? `, wait ${a.wait_s}s` : ''}` : (a.result ?? '') })}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <DataDiff before={entry.input} after={entry.output} beforeLabel={t('rp.before')}
              afterLabel={entry.output === undefined ? t('rp.noData') : t('rp.after')} />
          </div>
        </section>
      )}
    </Page>
  );
}

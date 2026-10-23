import { useEffect, useRef, useState } from 'react';

import { api, ApiError, type Report, type WorkflowNode } from '../api/client';
import { Icon } from '../components/Icon';
import { MiniLine } from '../components/MiniLine';
import { ErrorNote, Page } from '../components/Page';
import { StatusTag } from '../components/StatusTag';
import { useLang } from '../i18n/lang';
import { useLastRun } from '../lib/lastRun';
import { sampleName, workflowName } from '../lib/names';
import { link } from '../lib/route';
import { statusLook } from '../lib/status';
import { arrived, ticksNeeded, trainStop } from '../lib/train';
import { useLoad } from '../lib/useLoad';

const STEP_MS = 300;
const WAITING = ['review_pending', 'possible_duplicate'];

const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

// a file name -> a name the backend accepts (a-z 0-9 _ -, max 40)
const uploadName = (file: string) =>
  file.replace(/\.json$/i, '').toLowerCase().replace(/[^a-z0-9_-]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40) || 'upload';

export function RunStudioPage() {
  const { t } = useLang();
  const { setLast } = useLastRun();
  const workflows = useLoad(() => api.workflows());
  const samples = useLoad(() => api.samples());

  const [wfKey, setWfKey] = useState('dorosak_lessons');
  const [sample, setSample] = useState('lessons_good');
  const [dry, setDry] = useState(true);
  const [previewAs, setPreviewAs] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [result, setResult] = useState<{ report: Report; nodes: WorkflowNode[]; workflowKey: string } | null>(null);
  const [tick, setTick] = useState(0);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearInterval(timer.current), []);

  function play(report: Report) {
    window.clearInterval(timer.current);
    const end = ticksNeeded(report.items);
    if (reducedMotion()) {
      setTick(end);
      return;
    }
    setTick(0);
    timer.current = window.setInterval(() => {
      setTick(n => {
        if (n + 1 >= end) window.clearInterval(timer.current);
        return Math.min(n + 1, end);
      });
    }, STEP_MS);
  }

  async function run() {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const detail = await api.workflow(wfKey);
      const report = await api.run({ workflow: wfKey, sample, dry_run: dry,
        ...(dry && previewAs.trim() ? { approved_by: previewAs } : {}) });
      const next = { report, nodes: detail.nodes ?? [], workflowKey: wfKey };
      setResult(next);
      if (dry) setLast(next);
      play(report);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  }

  async function upload(file: File) {
    setError(null);
    try {
      const r = await api.upload(uploadName(file.name), await file.text());
      samples.reload();
      setSample(r.key);
      setNote(t('run.uploaded', { name: file.name, n: r.items }));
    } catch (e) {
      setError(e as ApiError);
    }
  }

  const report = result?.report;
  return (
    <Page title={t('run.title')} intro={t('run.intro')}>
      <ErrorNote error={workflows.error ?? samples.error} />

      <section className="card pad form">
        <div className="form-grid">
          <label className="field">
            <span>{t('run.workflow')}</span>
            <select value={wfKey} onChange={e => setWfKey(e.target.value)}>
              {workflows.data?.map(w => (
                <option key={w.key} value={w.key} disabled={!w.ok}>
                  {w.ok ? workflowName(w.key, t) : t('run.refused', { name: workflowName(w.key, t) })}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>{t('run.sample')}</span>
            <select value={sample} onChange={e => setSample(e.target.value)}>
              {samples.data?.map(s => (
                <option key={s.key} value={s.key}>{sampleName(s.key, t)} · {t('sample.items', { n: s.items })}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>{t('run.upload')}</span>
            <input type="file" accept=".json,application/json"
              onChange={e => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ''; }} />
          </label>
        </div>

        <label className="check">
          <input type="checkbox" checked={dry} onChange={e => setDry(e.target.checked)} />
          {t('run.dry')}
        </label>
        {dry ? (
          <label className="field narrow">
            <span>{t('run.previewAs')}</span>
            <input type="text" value={previewAs} onChange={e => setPreviewAs(e.target.value)} autoComplete="off" />
          </label>
        ) : (
          <p className="hint"><Icon name="pause" /> {t('run.reviewHint')}</p>
        )}

        <div className="buttons">
          <button type="button" className="btn btn-primary" onClick={run} disabled={busy}>
            {busy ? t('run.running') : t('run.start')}
          </button>
          {report && (
            <button type="button" className="btn" onClick={() => play(report)}>{t('run.again')}</button>
          )}
        </div>
        {note && <p className="result-line"><Icon name="check" /> {note}</p>}
      </section>

      <ErrorNote error={error} />

      {report && result && (
        <section className="card">
          <div className="meta">
            <h2>{workflowName(report.workflow_id, t)}</h2>
            <span className="muted">{t(`mode.${report.mode}`)}</span>
            {Object.entries(report.summary).map(([s, n]) => (
              <span key={s} className="count-tag"><StatusTag status={s} /> {n}</span>
            ))}
          </div>
          <ol className="lessons">
            {report.items.map((item, i) => {
              const done = arrived(item, tick);
              const look = statusLook(item.status);
              const stop = trainStop(item, result.nodes, tick);
              const replay = link('replay', { run: report.mode === 'dry-run' ? 'dry' : report.run_id, i: String(i) });
              return (
                <li key={i} className="lesson">
                  <span className="lesson-id mono">{String(item.source_id)}</span>
                  <MiniLine nodes={result.nodes} stop={stop} color={done ? look.color : 'var(--ink)'}
                    label={`${String(item.source_id)}: ${item.status}`} />
                  <span className="lesson-status">{done && <StatusTag status={item.status} />}</span>
                  <span className="lesson-words muted">{item.word_count ?? ''}</span>
                  <span className="lesson-error" dir="auto">{done && item.error}</span>
                  <span className="lesson-links">
                    <a href={replay}>{t('run.toReplay')}</a>
                    {done && report.mode !== 'dry-run' && WAITING.includes(item.status) && (
                      <a href={link('inbox')}>{t('run.toInbox')}</a>
                    )}
                  </span>
                </li>
              );
            })}
          </ol>
        </section>
      )}
    </Page>
  );
}

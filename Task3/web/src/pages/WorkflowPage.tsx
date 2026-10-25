import { useEffect, useRef, useState } from 'react';

import { api, type WorkflowDetail, type WorkflowNode, type WorkflowSummary } from '../api/client';
import { Icon } from '../components/Icon';
import { useLang } from '../i18n/lang';
import { DetailsSwitch, useDetails } from '../lib/details';
import { en, type Key } from '../i18n/strings';
import { languageName } from '../lib/names';

const TRIGGER: WorkflowNode = { id: 'trigger', type: 'trigger' };

// the real workflows first, the refused example last
const TAB_ORDER = ['dorosak_lessons', 'question_bank', 'malicious_example'];
const order = (key: string) => (TAB_ORDER.includes(key) ? TAB_ORDER.indexOf(key) : TAB_ORDER.length);

function nodeKey(type: string, part: 'checks' | 'stops' | 'label'): Key | null {
  const key = `node.${type}.${part}`;
  return key in en ? (key as Key) : null;
}

// the paragraph above the list already says this, so the lines do not repeat it
const REPEATED = /\. workflow\.json is a description, not code$/;
const shortError = (e: string) => e.replace(REPEATED, '');

function StationDot({ kind, selected }: { kind: 'start' | 'stop' | 'gate'; selected: boolean }) {
  const fill = selected ? 'var(--route)' : 'var(--card)';
  const mark = selected ? 'var(--card)' : 'var(--route)';
  return (
    <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true" className="icon">
      {kind === 'start' ? (
        // the start of the line is a bar, like the end of a metro line
        <rect x="11" y="3" width="8" height="24" rx="4" fill={fill} stroke="var(--route)" strokeWidth="3" />
      ) : (
        <circle cx="15" cy="15" r="10" fill={fill} stroke="var(--route)" strokeWidth="3" />
      )}
      {kind === 'gate' && <path d="M12.5 11v8M17.5 11v8" stroke={mark} strokeWidth="2" strokeLinecap="round" />}
    </svg>
  );
}

export function WorkflowPage() {
  const { t } = useLang();
  const details = useDetails();
  const [list, setList] = useState<WorkflowSummary[] | null>(null);
  const [key, setKey] = useState('dorosak_lessons');
  const [detail, setDetail] = useState<WorkflowDetail | null>(null);
  const [station, setStation] = useState<WorkflowNode | null>(null);
  const [failed, setFailed] = useState(false);
  const detailRef = useRef<HTMLDivElement>(null);

  // bring the station card into view, mostly for the phone where it is under a long line
  useEffect(() => {
    if (station) detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [station]);

  useEffect(() => {
    api.workflows().then(ws => setList([...ws].sort((a, b) => order(a.key) - order(b.key)))).catch(() => setFailed(true));
  }, []);

  useEffect(() => {
    setDetail(null);
    setStation(null);
    api.workflow(key).then(setDetail).catch(() => setFailed(true));
  }, [key]);

  const name = (k: string) => {
    const label = `wf.name.${k}`;
    return label in en ? t(label as Key) : k;
  };
  const stationLabel = (node: WorkflowNode) => {
    const label = nodeKey(node.type, 'label');
    return label ? t(label) : node.id;
  };

  return (
    <main className="wrap page">
      <div className="page-top">
        <div className="page-head">
          <h1>{t('wf.title')}</h1>
        </div>
        <div className="page-actions"><DetailsSwitch /></div>
      </div>

      {failed && <div className="card notice" role="alert">{t('common.noApi')}</div>}

      {list && (
        <div className="tabs" role="tablist" aria-label={t('wf.pick')}>
          {list.map(w => (
            <button key={w.key} type="button" role="tab" className="tab" aria-selected={w.key === key}
              onClick={() => setKey(w.key)}>
              {name(w.key)}
            </button>
          ))}
        </div>
      )}

      {!detail && !failed && <p className="muted">{t('common.loading')}</p>}

      {detail && (
        <section className="card" aria-labelledby="wf-heading">
          <div className="meta">
            <h2 id="wf-heading">{name(detail.key)}</h2>
            {detail.ok ? (
              <span className="muted">{t('wf.checked', { n: detail.nodes?.length ?? 0 })}</span>
            ) : (
              <span className="error-text">{t('wf.refusedBadge', { n: detail.errors.length })}</span>
            )}
            {details && detail.id && <span className="mono">{detail.id}{detail.version ? ` ${detail.version}` : ''}</span>}
            {detail.allowed_languages && (
              <span className="muted">
                {t(detail.allowed_languages.length === 1 ? 'wf.language' : 'wf.languages',
                  { list: detail.allowed_languages.map(c => languageName(c, t)).join(t('common.listSep')) })}
              </span>
            )}
          </div>

          {detail.ok && detail.nodes ? (
            <div className="metro">
              <ol>
                {[TRIGGER, ...detail.nodes].map(node => {
                  const kind = node === TRIGGER ? 'start' : node.type === 'manual_approval' ? 'gate' : 'stop';
                  const selected = station?.id === node.id;
                  return (
                    <li key={node.id} className="station">
                      <button type="button" className="station-btn" aria-pressed={selected}
                        onClick={() => setStation(selected ? null : node)}>
                        <StationDot kind={kind} selected={selected} />
                        <span className="station-name">{stationLabel(node)}</span>
                        {node === TRIGGER ? <span className="station-sub">{t('wf.triggerType')}</span>
                          : details && <span className="station-type">{node.type}</span>}
                        {kind === 'gate' && (
                          <span className="gate-note"><Icon name="pause" size={12} />{t('wf.gate')}</span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ol>
            </div>
          ) : (
            <div className="refused">
              <p className="refused-title"><Icon name="cross" /> <strong>{t('wf.refusedTitle')}</strong></p>
              <p className="muted">{t('wf.refusedWhy')}</p>
              <ul className="errors">
                {detail.errors.map(e => <li key={e}>{shortError(e)}</li>)}
              </ul>
            </div>
          )}

          {detail.ok && (
            <div className="detail" ref={detailRef} aria-live="polite">
              {station ? <StationDetail node={station} label={stationLabel(station)} />
                : <p className="muted">{t('wf.pickStation')}</p>}
            </div>
          )}

          {details && detail.mermaid && (
            <details className="source">
              <summary>{t('wf.mermaid')}</summary>
              <pre className="json">{detail.mermaid}</pre>
            </details>
          )}
        </section>
      )}

    </main>
  );
}

function StationDetail({ node, label }: { node: WorkflowNode; label: string }) {
  const { t } = useLang();
  const details = useDetails();
  const isTrigger = node === TRIGGER;
  const checks = nodeKey(node.type, 'checks');
  const stops = nodeKey(node.type, 'stops');
  return (
    <>
      <div>
        <h3>{label}</h3>
        {details && !isTrigger && <span className="station-type">{node.id} · {node.type}</span>}
      </div>
      <dl>
        {checks && (<div><dt>{t('wf.checks')}</dt><dd>{t(checks)}</dd></div>)}
        {stops && (<div><dt>{t('wf.stops')}</dt><dd>{t(stops)}</dd></div>)}
        {details && !isTrigger && (
          <div>
            <dt>{t('wf.node')}</dt>
            <dd><pre className="json">{JSON.stringify(node, null, 2)}</pre></dd>
          </div>
        )}
      </dl>
    </>
  );
}

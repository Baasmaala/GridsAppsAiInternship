import { useState } from 'react';

import { api, ApiError, type ReviewItem } from '../api/client';
import { DataDiff } from '../components/DataDiff';
import { Icon } from '../components/Icon';
import { Empty, ErrorNote, Page } from '../components/Page';
import { StatusTag } from '../components/StatusTag';
import { useLang } from '../i18n/lang';
import { workflowName } from '../lib/names';
import { canApprove, canReject } from '../lib/review';
import { formatTime, shortId } from '../lib/time';
import { useLoad } from '../lib/useLoad';

const NAME_KEY = 'masar.reviewer';

// only a convenience for this browser. it is not who you are.
function savedName(): string {
  try {
    return localStorage.getItem(NAME_KEY) ?? '';
  } catch {
    return '';
  }
}

export function InboxPage() {
  const { t } = useLang();
  const inbox = useLoad(() => api.reviews());
  const [name, setName] = useState(savedName);
  const [done, setDone] = useState<string[]>([]);

  function changeName(value: string) {
    setName(value);
    try {
      localStorage.setItem(NAME_KEY, value);
    } catch {
      // private window: fine, it is just not remembered
    }
  }

  const finished = (line: string) => {
    setDone(d => [line, ...d]);
    inbox.reload();
  };

  return (
    <Page title={t('ib.title')} intro={t('ib.intro')}>
      <section className="card pad form">
        <label className="field narrow">
          <span>{t('ib.name')}</span>
          <input type="text" value={name} onChange={e => changeName(e.target.value)} autoComplete="off" />
        </label>
        <p className="hint">{t('ib.nameNote')}</p>
      </section>

      {done.length > 0 && (
        <section className="card pad">
          <h2 className="card-title flush">{t('ib.done')}</h2>
          <ul className="plain">{done.map((line, i) => <li key={i} className="result-line"><Icon name="check" /> {line}</li>)}</ul>
        </section>
      )}

      <ErrorNote error={inbox.error} />
      {inbox.data?.length === 0 && <Empty>{t('ib.empty')}</Empty>}
      {inbox.data?.map(item => (
        <ReviewCard key={`${item.run_id}/${item.source_id}`} item={item} name={name} onDone={finished} />
      ))}
    </Page>
  );
}

function ReviewCard({ item, name, onDone }: { item: ReviewItem; name: string; onDone: (line: string) => void }) {
  const { t, lang } = useLang();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  async function decide(decision: 'approve' | 'reject') {
    setBusy(true);
    setError(null);
    try {
      const r = await api.decide(item.run_id, item.source_id, { reviewer: name, decision, reason });
      const out = r.items[0];
      const reviewer = name.trim();
      onDone(out.status === 'draft_saved' ? t('ib.saved', { id: out.source_id, name: reviewer })
        : out.status === 'rejected' ? t('ib.rejected', { id: out.source_id, name: reviewer, reason: reason.trim() })
          : t('ib.stillWaiting', { id: out.source_id, status: out.status }));
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  }

  const title = String(item.normalized.title ?? item.normalized.question ?? item.source_id);
  return (
    <section className="card review">
      <div className="meta">
        <h2 dir="auto">{title}</h2>
        <StatusTag status={item.status} />
        <span className="mono muted">{item.source_id}</span>
        <span className="muted">{workflowName(item.workflow_id, t)}</span>
        {typeof item.word_count === 'number' && <span className="muted">{t('ib.words', { n: item.word_count })}</span>}
        <span className="mono muted">{t('ib.run', { id: shortId(item.run_id) })} · {formatTime(item.created_at, lang)}</span>
      </div>

      <div className="pad">
        <DataDiff before={item.original} after={item.normalized} beforeLabel={t('ib.original')}
          afterLabel={t('ib.normalized')} />
      </div>

      {item.possible_duplicate_of && (
        <div className="pad lookalike">
          {item.old_draft ? (
            <>
              <p><Icon name="dot" /> {t('ib.lookalike', { id: item.possible_duplicate_of })}</p>
              <dl className="old-draft">
                <dt>title</dt><dd dir="auto">{String(item.old_draft.title ?? item.old_draft.question ?? '')}</dd>
                <dt>status</dt><dd>{String(item.old_draft.status)}</dd>
                <dt>reviewed_by</dt><dd>{String(item.old_draft.reviewed_by ?? '')}</dd>
                <dt>saved_at</dt><dd>{item.old_draft.saved_at ? formatTime(String(item.old_draft.saved_at), lang) : ''}</dd>
              </dl>
            </>
          ) : (
            <p><Icon name="dot" /> {t('ib.lookalikeRun', { id: item.possible_duplicate_of })}</p>
          )}
        </div>
      )}

      <div className="pad decide">
        {rejecting ? (
          <>
            <label className="field">
              <span>{t('ib.reason')}</span>
              <textarea rows={2} value={reason} onChange={e => setReason(e.target.value)} dir="auto" />
            </label>
            <div className="buttons">
              <button type="button" className="btn btn-danger" disabled={busy || !canReject(name, reason)}
                onClick={() => decide('reject')}>{t('ib.confirmReject')}</button>
              <button type="button" className="btn" onClick={() => setRejecting(false)} disabled={busy}>{t('ov.cancel')}</button>
            </div>
            {!canReject(name, reason) && (
              <p className="hint">{!canApprove(name) ? t('ib.needName') : t('ib.needReason')}</p>
            )}
          </>
        ) : (
          <>
            <div className="buttons">
              <button type="button" className="btn btn-primary" disabled={busy || !canApprove(name)}
                onClick={() => decide('approve')}><Icon name="check" /> {t('ib.approve')}</button>
              <button type="button" className="btn" disabled={busy} onClick={() => setRejecting(true)}>
                <Icon name="cross" /> {t('ib.reject')}</button>
            </div>
            {!canApprove(name) && <p className="hint">{t('ib.needName')}</p>}
          </>
        )}
        <ErrorNote error={error} />
      </div>
    </section>
  );
}

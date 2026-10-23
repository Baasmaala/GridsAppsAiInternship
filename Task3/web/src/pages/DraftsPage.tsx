import { api } from '../api/client';
import { Empty, ErrorNote, Page } from '../components/Page';
import { Badge } from '../components/StatusTag';
import { useLang } from '../i18n/lang';
import { draftsFileWorkflow, workflowName } from '../lib/names';
import { formatTime } from '../lib/time';
import { useLoad } from '../lib/useLoad';

export function DraftsPage() {
  const { t, lang } = useLang();
  const drafts = useLoad(() => api.drafts());

  return (
    <Page title={t('dr.title')} intro={t('dr.intro')}>
      <ErrorNote error={drafts.error} />
      {drafts.data?.length === 0 && <Empty>{t('dr.empty')}</Empty>}
      <div className="draft-list">
        {[...(drafts.data ?? [])].reverse().map(({ file, draft }) => {
          const title = String(draft.title ?? draft.question ?? draft.source_id);
          return (
            <article key={`${file}/${String(draft.source_id)}`} className="card pad draft">
              <div className="draft-top">
                <Badge color="var(--ok)">{t('dr.badge')}</Badge>
                <span className="mono muted">{String(draft.source_id)}</span>
              </div>
              <h2 dir="auto">{title}</h2>
              <p className="muted">
                {workflowName(draftsFileWorkflow(file), t)}
                {draft.level ? ` · ${String(draft.level)}` : ''}
                {typeof draft.word_count === 'number' ? ` · ${t('ib.words', { n: draft.word_count })}` : ''}
              </p>
              <p className="muted">
                {t('dr.by', { name: String(draft.reviewed_by ?? '') })}
                {draft.saved_at ? ` · ${t('dr.at', { time: formatTime(String(draft.saved_at), lang) })}` : ''}
              </p>
              {typeof draft.possible_duplicate_of === 'string' && (
                <p className="muted">{t('dr.like', { id: draft.possible_duplicate_of })}</p>
              )}
            </article>
          );
        })}
      </div>
    </Page>
  );
}

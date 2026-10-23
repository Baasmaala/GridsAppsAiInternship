import { useEffect, useRef, useState, type FormEvent } from 'react';

import { api, ApiError } from '../api/client';
import { useLang } from '../i18n/lang';
import type { Key } from '../i18n/strings';
import { askBody, sourceLine, type AskContext, type AskSource } from '../lib/ask';
import { shortId } from '../lib/time';
import { Icon } from './Icon';
import { ErrorNote } from './Page';

type Note = { question: string; answer: string; source: AskSource };

const EXAMPLES: Key[] = ['ask.ex1', 'ask.ex2', 'ask.ex3', 'ask.ex4'];

// a notes column, not a chat: the question in bold, the answer under it, where it came from in mono
export function AskPanel({ open, onClose, context }: { open: boolean; onClose: () => void; context: AskContext }) {
  const { t, lang } = useLang();
  const [question, setQuestion] = useState('');
  const [notes, setNotes] = useState<Note[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const box = useRef<HTMLTextAreaElement>(null);
  const list = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    box.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  // only the notes column scrolls to the newest answer, never the page behind it
  useEffect(() => {
    if (list.current) list.current.scrollTop = list.current.scrollHeight;
  }, [notes]);

  async function ask(text: string) {
    if (!text.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.chat(askBody(text, lang, context));
      setNotes(n => [...n, { question: text.trim(), answer: r.answer, source: r.source }]);
      setQuestion('');
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  }

  const submit = (e: FormEvent) => { e.preventDefault(); ask(question); };

  if (!open) return null;
  const looking = context.kind === 'run' ? t('ask.lookRun', { run: shortId(context.runId), n: context.index + 1 })
    : context.kind === 'dry' ? t('ask.lookDry', { id: context.sourceId }) : null;

  return (
    <aside className="ask" aria-labelledby="ask-title">
      <div className="ask-head">
        <h2 id="ask-title">{t('ask.title')}</h2>
        <button type="button" className="btn ask-close" onClick={onClose}>
          <Icon name="cross" size={14} /> {t('ask.close')}
        </button>
      </div>
      <p className="ask-looking muted">{looking ? t('ask.looking', { what: looking }) : t('ask.noRun')}</p>

      <div className="ask-notes" aria-live="polite" ref={list}>
        {notes.length === 0 && (
          <div className="ask-try">
            <p className="muted">{t('ask.try')}</p>
            <ul className="plain">
              {EXAMPLES.map(k => (
                <li key={k}><button type="button" className="ask-example" onClick={() => ask(t(k))} disabled={busy}>{t(k)}</button></li>
              ))}
            </ul>
          </div>
        )}
        {notes.map((n, i) => (
          <article key={i} className="ask-note">
            <p className="ask-q" dir="auto">{n.question}</p>
            <p className="ask-a" dir="auto">{n.answer}</p>
            <p className="ask-src mono">{sourceLine(n.source)}</p>
          </article>
        ))}
      </div>

      <form className="ask-form" onSubmit={submit}>
        <label className="field">
          <span>{t('ask.label')}</span>
          <textarea ref={box} rows={2} maxLength={500} value={question} dir="auto"
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(question); } }} />
        </label>
        <button type="submit" className="btn btn-primary" disabled={busy || !question.trim()}>
          {busy ? t('ask.sending') : t('ask.send')}
        </button>
        <ErrorNote error={error} />
        <p className="ask-rule muted">{t('ask.note')}</p>
      </form>
    </aside>
  );
}

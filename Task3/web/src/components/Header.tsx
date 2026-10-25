import { useLang } from '../i18n/lang';
import type { Key } from '../i18n/strings';
import { MasarMark } from './MasarMark';

export type PageId = 'overview' | 'workflow' | 'run' | 'replay' | 'inbox' | 'drafts' | 'audit' | 'lab';

export const PAGES: { id: PageId; label: Key; ready: boolean }[] = [
  { id: 'overview', label: 'nav.overview', ready: true },
  { id: 'workflow', label: 'nav.workflow', ready: true },
  { id: 'run', label: 'nav.run', ready: true },
  { id: 'replay', label: 'nav.replay', ready: true },
  { id: 'inbox', label: 'nav.inbox', ready: true },
  { id: 'drafts', label: 'nav.drafts', ready: true },
  { id: 'audit', label: 'nav.audit', ready: true },
  { id: 'lab', label: 'nav.lab', ready: true },
];

export function Header({ page, onAsk, asking }: { page: PageId; onAsk: () => void; asking: boolean }) {
  const { t, toggle, lang } = useLang();
  return (
    <header className="header">
      <div className="wrap header-row">
        {/* the logo is the same in both languages, it never flips with rtl */}
        <a className="brand" href="#/overview" dir="ltr">
          <MasarMark size={40} />
          <span className="brand-name">Masar</span>
          <span className="brand-ar" lang="ar">مسار</span>
        </a>
        <nav className="nav" aria-label="Pages">
          {PAGES.map(p =>
            p.ready ? (
              <a key={p.id} href={`#/${p.id}`} aria-current={p.id === page ? 'page' : undefined}>{t(p.label)}</a>
            ) : (
              <span key={p.id} aria-disabled="true">{t(p.label)}</span>
            ),
          )}
        </nav>
        <button type="button" className="lang-switch ask-button" onClick={onAsk} aria-expanded={asking}>
          {t('ask.button')}
        </button>
        <button type="button" className="lang-switch" onClick={toggle} lang={lang === 'en' ? 'ar' : 'en'}>
          {t('lang.switch')}
        </button>
      </div>
    </header>
  );
}

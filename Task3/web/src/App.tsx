import { useEffect, useState } from 'react';

import { Header, PAGES, type PageId } from './components/Header';
import { LangProvider } from './i18n/lang';
import { WorkflowPage } from './pages/WorkflowPage';

// a tiny hash router: #/workflow. no router package needed.
function pageFromHash(): PageId {
  const id = window.location.hash.replace(/^#\//, '');
  const page = PAGES.find(p => p.id === id && p.ready);
  return page ? page.id : 'workflow';
}

export function App() {
  const [page, setPage] = useState<PageId>(pageFromHash);

  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  return (
    <LangProvider>
      <Header page={page} />
      {page === 'workflow' && <WorkflowPage />}
    </LangProvider>
  );
}

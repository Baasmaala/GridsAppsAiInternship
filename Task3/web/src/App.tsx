import { useEffect, useState } from 'react';

import { Header, PAGES, type PageId } from './components/Header';
import { LangProvider } from './i18n/lang';
import { LastRunProvider } from './lib/lastRun';
import { parseHash } from './lib/route';
import { AuditPage } from './pages/AuditPage';
import { DraftsPage } from './pages/DraftsPage';
import { InboxPage } from './pages/InboxPage';
import { LabPage } from './pages/LabPage';
import { OverviewPage } from './pages/OverviewPage';
import { ReplayPage } from './pages/ReplayPage';
import { RunStudioPage } from './pages/RunStudioPage';
import { WorkflowPage } from './pages/WorkflowPage';

// a tiny hash router: #/replay?run=...&i=2. no router package needed.
function current(): { page: PageId; params: URLSearchParams } {
  const { page, params } = parseHash(window.location.hash);
  const found = PAGES.find(p => p.id === page);
  return { page: found ? found.id : 'overview', params };
}

export function App() {
  const [route, setRoute] = useState(current);

  useEffect(() => {
    const onHash = () => {
      setRoute(current());
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  return (
    <LangProvider>
      <LastRunProvider>
        <Header page={route.page} />
        {route.page === 'overview' && <OverviewPage />}
        {route.page === 'workflow' && <WorkflowPage />}
        {route.page === 'run' && <RunStudioPage />}
        {route.page === 'replay' && <ReplayPage params={route.params} />}
        {route.page === 'inbox' && <InboxPage />}
        {route.page === 'drafts' && <DraftsPage />}
        {route.page === 'audit' && <AuditPage />}
        {route.page === 'lab' && <LabPage />}
      </LastRunProvider>
    </LangProvider>
  );
}

import { useCallback, useEffect, useState } from 'react';

import { AskPanel } from './components/AskPanel';
import { Header, PAGES, type PageId } from './components/Header';
import { LangProvider } from './i18n/lang';
import { askContext } from './lib/ask';
import { DetailsProvider } from './lib/details';
import { LastRunProvider, useLastRun } from './lib/lastRun';
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
  return (
    <LangProvider>
      <DetailsProvider>
        <LastRunProvider>
          <Shell />
        </LastRunProvider>
      </DetailsProvider>
    </LangProvider>
  );
}

function Shell() {
  const [route, setRoute] = useState(current);
  const [asking, setAsking] = useState(false);
  const { last } = useLastRun();
  const closeAsk = useCallback(() => setAsking(false), []);

  useEffect(() => {
    const onHash = () => {
      setRoute(current());
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  return (
    <>
      <Header page={route.page} onAsk={() => setAsking(a => !a)} asking={asking} />
      {route.page === 'overview' && <OverviewPage />}
      {route.page === 'workflow' && <WorkflowPage />}
      {route.page === 'run' && <RunStudioPage />}
      {route.page === 'replay' && <ReplayPage params={route.params} />}
      {route.page === 'inbox' && <InboxPage />}
      {route.page === 'drafts' && <DraftsPage />}
      {route.page === 'audit' && <AuditPage />}
      {route.page === 'lab' && <LabPage />}
      <AskPanel open={asking} onClose={closeAsk} context={askContext(route.page, route.params, last)} />
    </>
  );
}

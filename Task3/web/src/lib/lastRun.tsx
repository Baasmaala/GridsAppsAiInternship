import { createContext, useContext, useState, type ReactNode } from 'react';

import type { Report, WorkflowNode } from '../api/client';

// a dry run is never saved by the backend, so Replay gets the last one from here (memory only)
type LastRun = { report: Report; nodes: WorkflowNode[]; workflowKey: string } | null;

const Ctx = createContext<{ last: LastRun; setLast: (r: LastRun) => void } | null>(null);

export function LastRunProvider({ children }: { children: ReactNode }) {
  const [last, setLast] = useState<LastRun>(null);
  return <Ctx.Provider value={{ last, setLast }}>{children}</Ctx.Provider>;
}

export function useLastRun() {
  const v = useContext(Ctx);
  if (!v) throw new Error('useLastRun needs a LastRunProvider');
  return v;
}

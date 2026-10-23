import { useCallback, useEffect, useState } from 'react';

import { ApiError } from '../api/client';

export type Load<T> = { data: T | null; error: ApiError | null; loading: boolean; reload: () => void };

// fetch once on mount, and again when reload() is called
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = []): Load<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [round, setRound] = useState(0);

  useEffect(() => {
    let live = true;
    setLoading(true);
    fn().then(d => { if (live) { setData(d); setError(null); } })
      .catch(e => { if (live) setError(e instanceof ApiError ? e : new ApiError(0, String(e))); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [round, ...deps]);

  const reload = useCallback(() => setRound(r => r + 1), []);
  return { data, error, loading, reload };
}

import { createContext, useContext, useState, type ReactNode } from 'react';

import { useLang } from '../i18n/lang';

const STORE_KEY = 'masar.details';

function savedShow(): boolean {
  try {
    return localStorage.getItem(STORE_KEY) === '1';
  } catch {
    return false;
  }
}

// one switch for the whole app: ids, raw status names and hashes are hidden until it is on
const DetailsContext = createContext<{ show: boolean; setShow: (on: boolean) => void } | null>(null);

export function DetailsProvider({ children }: { children: ReactNode }) {
  const [show, setState] = useState(savedShow);
  const setShow = (on: boolean) => {
    setState(on);
    try {
      localStorage.setItem(STORE_KEY, on ? '1' : '0');
    } catch {
      // private window: fine, it is just not remembered
    }
  };
  return <DetailsContext.Provider value={{ show, setShow }}>{children}</DetailsContext.Provider>;
}

export function useDetails(): boolean {
  const ctx = useContext(DetailsContext);
  if (!ctx) throw new Error('useDetails needs a DetailsProvider');
  return ctx.show;
}

export function DetailsSwitch() {
  const ctx = useContext(DetailsContext);
  const { t } = useLang();
  if (!ctx) return null;
  return (
    <label className="check details-switch">
      <input type="checkbox" checked={ctx.show} onChange={e => ctx.setShow(e.target.checked)} />
      {t('details.show')}
    </label>
  );
}

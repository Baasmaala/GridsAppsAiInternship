import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

import { STRINGS, dirFor, format, type Key, type Lang } from './strings';

const STORE_KEY = 'masar.lang';

function savedLang(): Lang {
  try {
    return localStorage.getItem(STORE_KEY) === 'ar' ? 'ar' : 'en';
  } catch {
    return 'en';
  }
}

type LangApi = { lang: Lang; toggle: () => void; t: (key: Key, vars?: Record<string, string | number>) => string };

const LangContext = createContext<LangApi | null>(null);

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(savedLang);

  useEffect(() => {
    // the whole page flips, not only the text
    document.documentElement.lang = lang;
    document.documentElement.dir = dirFor(lang);
    try {
      localStorage.setItem(STORE_KEY, lang);
    } catch {
      // private window: the switch still works, it is just not remembered
    }
  }, [lang]);

  const api: LangApi = {
    lang,
    toggle: () => setLang(l => (l === 'en' ? 'ar' : 'en')),
    t: (key, vars) => format(STRINGS[lang][key], vars, lang),
  };
  return <LangContext.Provider value={api}>{children}</LangContext.Provider>;
}

export function useLang(): LangApi {
  const api = useContext(LangContext);
  if (!api) throw new Error('useLang needs a LangProvider');
  return api;
}

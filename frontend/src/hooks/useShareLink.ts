/** Load shared code from the URL hash on startup and build share links. */
import { useCallback, useEffect } from 'react';

import { useAppStore } from '../stores/appStore';
import { decodeShare, encodeShare } from '../utils/share';

export function useShareLink(onLoaded: () => void) {
  useEffect(() => {
    const shared = decodeShare(window.location.hash);
    if (!shared) return;
    const { setCode, setLanguage, setEntryCall } = useAppStore.getState();
    setCode(shared.code);
    setLanguage(shared.language);
    setEntryCall(shared.entryCall ?? '');
    onLoaded();
    // run once on mount only
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Copy a link reproducing the current editor state; resolves to the URL. */
  return useCallback(async (): Promise<string> => {
    const { code, language, entryCall } = useAppStore.getState();
    const url = `${window.location.origin}${window.location.pathname}${encodeShare({ code, language, entryCall })}`;
    window.history.replaceState(null, '', url);
    await navigator.clipboard?.writeText(url).catch(() => undefined);
    return url;
  }, []);
}

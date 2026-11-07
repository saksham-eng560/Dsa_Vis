/** Reflects the store's theme onto <html data-theme> so CSS tokens switch. */
import { useEffect } from 'react';

import { useAppStore } from '../stores/appStore';

export function useTheme() {
  const theme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  return { theme, toggleTheme };
}

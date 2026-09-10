import { useEffect, useState } from 'react';
import type { Theme } from '../types/editor';

const THEME_KEY = 'soniccraft-theme';

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    try { return window.localStorage.getItem(THEME_KEY) === 'light' ? 'light' : 'dark'; }
    catch { return 'dark'; }
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { window.localStorage.setItem(THEME_KEY, theme); } catch { /* Storage may be disabled. */ }
  }, [theme]);

  return {
    theme,
    toggleTheme: () => setTheme((current) => (current === 'dark' ? 'light' : 'dark')),
  };
}

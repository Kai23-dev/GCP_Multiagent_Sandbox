'use client';

import { useState, useEffect } from 'react';
import { Theme, getCurrentTheme, setTheme as saveTheme } from '@/styles/themes';

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(getCurrentTheme());

  useEffect(() => {
    // Load theme on mount
    setThemeState(getCurrentTheme());

    // Listen for theme changes
    const handleThemeChange = () => {
      setThemeState(getCurrentTheme());
    };

    window.addEventListener('themeChange', handleThemeChange);

    return () => {
      window.removeEventListener('themeChange', handleThemeChange);
    };
  }, []);

  const setTheme = (themeName: string) => {
    saveTheme(themeName);
    setThemeState(getCurrentTheme());
  };

  return { theme, setTheme };
}

/**
 * Theme Configuration
 * Supports multiple themes including default and DaVita branding
 */

export interface Theme {
  name: string;
  colors: {
    // Primary colors
    primary: {
      light: string;
      main: string;
      dark: string;
      gradient: string;
    };
    // Secondary colors
    secondary: {
      light: string;
      main: string;
      dark: string;
      gradient: string;
    };
    // Accent colors for special features
    accent: {
      light: string;
      main: string;
      dark: string;
      gradient: string;
    };
    // Memory bank specific colors
    memory: {
      save: string;
      browser: string;
      success: string;
    };
    // UI colors
    background: {
      main: string;
      secondary: string;
      hover: string;
    };
    text: {
      primary: string;
      secondary: string;
      light: string;
    };
  };
}

// Default modern theme (purple/pink)
export const defaultTheme: Theme = {
  name: 'default',
  colors: {
    primary: {
      light: '#a78bfa',
      main: '#8b5cf6',
      dark: '#7c3aed',
      gradient: 'from-purple-500 to-pink-500',
    },
    secondary: {
      light: '#818cf8',
      main: '#6366f1',
      dark: '#4f46e5',
      gradient: 'from-indigo-500 to-purple-500',
    },
    accent: {
      light: '#f0abfc',
      main: '#e879f9',
      dark: '#d946ef',
      gradient: 'from-pink-500 to-rose-500',
    },
    memory: {
      save: 'from-purple-500 to-pink-500',
      browser: 'from-indigo-500 to-purple-500',
      success: 'from-green-500 to-emerald-500',
    },
    background: {
      main: '#ffffff',
      secondary: '#f9fafb',
      hover: '#f3f4f6',
    },
    text: {
      primary: '#111827',
      secondary: '#6b7280',
      light: '#9ca3af',
    },
  },
};

// DaVita brand theme (authentic colors from davita.com)
export const davitaTheme: Theme = {
  name: 'davita',
  colors: {
    primary: {
      light: '#ff8c42', // Lighter coral-orange
      main: '#ff6b35',  // DaVita coral-orange (primary brand color)
      dark: '#e55a2b',  // Darker coral
      gradient: 'from-orange-500 to-orange-600', // Coral orange gradient
    },
    secondary: {
      light: '#4fc3dc', // Lighter teal
      main: '#00a9ce',  // DaVita teal (secondary brand color)
      dark: '#008bb3',  // Darker teal
      gradient: 'from-cyan-500 to-teal-500', // Teal gradient
    },
    accent: {
      light: '#ffa94d',
      main: '#ff8800',  // Warm orange accent
      dark: '#e67700',
      gradient: 'from-amber-500 to-orange-500',
    },
    memory: {
      save: 'from-orange-500 to-orange-600',     // Coral orange
      browser: 'from-cyan-500 to-teal-500',      // Teal
      success: 'from-green-500 to-emerald-500',
    },
    background: {
      main: '#ffffff',
      secondary: '#f7f9fa', // Very light gray (DaVita clean look)
      hover: '#eef2f5',
    },
    text: {
      primary: '#1a1a1a',   // Almost black (DaVita uses dark text)
      secondary: '#5a6169', // Medium gray
      light: '#878d96',     // Light gray
    },
  },
};

// Theme map for easy access
export const themes: Record<string, Theme> = {
  default: defaultTheme,
  davita: davitaTheme,
};

// Get current theme from localStorage or default
export function getCurrentTheme(): Theme {
  if (typeof window !== 'undefined') {
    const savedTheme = localStorage.getItem('appTheme');
    return themes[savedTheme || 'default'] || defaultTheme;
  }
  return defaultTheme;
}

// Set theme
export function setTheme(themeName: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('appTheme', themeName);
    window.dispatchEvent(new CustomEvent('themeChange', { detail: themeName }));
  }
}

// Get all available themes
export function getAvailableThemes(): Theme[] {
  return Object.values(themes);
}

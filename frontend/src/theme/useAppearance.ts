import { createContext, useContext } from 'react';

import type { Appearance, PaletteName } from './appearance';

export interface AppearanceContextValue extends Appearance {
  setPalette: (palette: PaletteName) => void;
  toggleDark: () => void;
}

export const AppearanceContext = createContext<AppearanceContextValue | null>(null);

export function useAppearance() {
  const value = useContext(AppearanceContext);
  if (!value) {
    throw new Error('useAppearance harus digunakan di dalam AppearanceProvider.');
  }
  return value;
}

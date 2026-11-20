import { createContext } from 'react';

import type { UserProfile } from '../../types/api';
import type { PaletteName } from '../../theme/appearance';

export type { PaletteName };

export interface LandingEnv {
  user: UserProfile | null;
  authLoading: boolean;
  login: (nextUrl?: string) => void;
  logout: () => void;
  /** Gulir halus ke seksi dengan data-sec = id. */
  go: (id: string) => void;
  palette: PaletteName;
  setPalette: (p: PaletteName) => void;
  dark: boolean;
  toggleDark: () => void;
}

export const LandingCtx = createContext<LandingEnv>({
  user: null,
  authLoading: false,
  login: () => {},
  logout: () => {},
  go: () => {},
  palette: 'meadow',
  setPalette: () => {},
  dark: false,
  toggleDark: () => {},
});

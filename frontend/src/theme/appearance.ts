export type PaletteName = 'meadow' | 'lavender' | 'harvest';

export interface Appearance {
  dark: boolean;
  palette: PaletteName;
}

export const DEFAULT_APPEARANCE: Appearance = {
  dark: false,
  palette: 'meadow',
};

const APPEARANCE_STORAGE_KEY = 'judolguard.appearance';

function isPaletteName(value: unknown): value is PaletteName {
  return value === 'meadow' || value === 'lavender' || value === 'harvest';
}

export function readAppearance(): Appearance {
  if (typeof window === 'undefined') return DEFAULT_APPEARANCE;

  try {
    const raw = window.localStorage.getItem(APPEARANCE_STORAGE_KEY);
    if (!raw) return DEFAULT_APPEARANCE;
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return DEFAULT_APPEARANCE;

    const value = parsed as Partial<Appearance>;
    return {
      dark: value.dark === true,
      palette: isPaletteName(value.palette) ? value.palette : DEFAULT_APPEARANCE.palette,
    };
  } catch {
    return DEFAULT_APPEARANCE;
  }
}

export function applyAppearance(appearance: Appearance) {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;
  root.dataset.appTheme = appearance.dark ? 'dark' : 'light';
  root.dataset.appPalette = appearance.palette;
  root.style.colorScheme = appearance.dark ? 'dark' : 'light';
}

export function persistAppearance(appearance: Appearance) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(APPEARANCE_STORAGE_KEY, JSON.stringify(appearance));
  } catch {
    // Tema tetap aktif di sesi ini walaupun storage browser tidak tersedia.
  }
}

export function initializeAppearance() {
  const appearance = readAppearance();
  applyAppearance(appearance);
  return appearance;
}

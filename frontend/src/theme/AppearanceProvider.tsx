import {
  type PropsWithChildren,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useState,
} from 'react';

import {
  applyAppearance,
  initializeAppearance,
  persistAppearance,
  type Appearance,
  type PaletteName,
} from './appearance';
import { AppearanceContext } from './useAppearance';

export function AppearanceProvider({ children }: PropsWithChildren) {
  const [appearance, setAppearance] = useState<Appearance>(initializeAppearance);

  useLayoutEffect(() => {
    applyAppearance(appearance);
  }, [appearance]);

  useEffect(() => {
    persistAppearance(appearance);
  }, [appearance]);

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key !== 'judolguard.appearance') return;
      const next = initializeAppearance();
      setAppearance(next);
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const setPalette = useCallback((palette: PaletteName) => {
    setAppearance((current) => ({ ...current, palette }));
  }, []);

  const toggleDark = useCallback(() => {
    setAppearance((current) => ({ ...current, dark: !current.dark }));
  }, []);

  const value = useMemo(
    () => ({ ...appearance, setPalette, toggleDark }),
    [appearance, setPalette, toggleDark],
  );

  return <AppearanceContext.Provider value={value}>{children}</AppearanceContext.Provider>;
}

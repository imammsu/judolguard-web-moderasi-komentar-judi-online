import { Moon, Sun } from 'lucide-react';

import { useAppearance } from '../theme/useAppearance';

export default function AppearanceControls() {
  const { dark, toggleDark } = useAppearance();

  return (
    <div className="flex items-center" aria-label="Pengaturan tampilan">
      <button
        type="button"
        onClick={toggleDark}
        aria-label={dark ? 'Gunakan mode terang' : 'Gunakan mode gelap'}
        title={dark ? 'Gunakan mode terang' : 'Gunakan mode gelap'}
        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
      >
        {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>
    </div>
  );
}

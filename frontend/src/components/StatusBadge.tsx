import type { ReactNode } from 'react';

type Tone = 'ok' | 'warn' | 'error' | 'muted';

const toneClass: Record<Tone, string> = {
  ok: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  warn: 'bg-amber-50 text-amber-700 ring-amber-200',
  error: 'bg-rose-50 text-rose-700 ring-rose-200',
  muted: 'bg-slate-100 text-slate-600 ring-slate-200',
};

export default function StatusBadge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${toneClass[tone]}`}
    >
      {children}
    </span>
  );
}

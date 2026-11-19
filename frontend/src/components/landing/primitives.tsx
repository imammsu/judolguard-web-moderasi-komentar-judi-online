import * as React from 'react';

import { hueOf, initials } from './utils';

const ICONS: Record<string, string> = {
  arrow: 'M5 12h13m-5-5 5 5-5 5',
  down: 'm6 9 6 6 6-6',
  check: 'm5 12.5 4.2 4.2L19 7',
  plus: 'M12 5v14M5 12h14',
  menu: 'M4 7h16M4 12h16M4 17h16',
  close: 'M6 6l12 12M18 6 6 18',
  inbox: 'M4 13.5 6.5 5h11l2.5 8.5V19H4v-5.5Zm0 0h5l1 2h4l1-2h5',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8c.8-3.5 3.6-5.5 7-5.5s6.2 2 7 5.5',
  spark: 'M12 3.5 13.8 9l5.7 1.9-5.7 1.9L12 18.5l-1.8-5.7L4.5 11l5.7-1.9L12 3.5Z',
  hand: 'M8 11V5.5a1.5 1.5 0 0 1 3 0V11m0-1V4.5a1.5 1.5 0 0 1 3 0V11m0-.5V6a1.5 1.5 0 0 1 3 0v7c0 4-2.5 7-6.5 7-3 0-4.5-1.5-6-4l-1.8-3a1.5 1.5 0 0 1 2.6-1.5L8 13',
  chat: 'M5 5.5h14v10H10l-4 3.5v-3.5H5v-10Z',
  search: 'M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm5-2 4 4',
  book: 'M5 4.5h9a3 3 0 0 1 3 3V20a2.5 2.5 0 0 0-2.5-2.5H5v-13Zm12 3a3 3 0 0 1 3-3v13a2.5 2.5 0 0 0-2.5 2.5',
  shield: 'M12 3.5 19 6v5.5c0 4.5-3 7.8-7 9-4-1.2-7-4.5-7-9V6l7-2.5Zm-3 8.5 2.2 2.2L15.5 10',
  lock: 'M6.5 11h11v9h-11v-9Zm2.5 0V8a3 3 0 0 1 6 0v3m-3 3.5v2',
  key: 'M14.5 9.5a4 4 0 1 1-1.2-2.8 4 4 0 0 1 1.2 2.8Zm-1.2 2.8L20 19m-3-3 2-2',
  eye: 'M2.5 12s3.5-6.5 9.5-6.5 9.5 6.5 9.5 6.5-3.5 6.5-9.5 6.5S2.5 12 2.5 12Zm9.5 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z',
  tag: 'M4 4.5h7.5l8.5 8.5-7 7-8.5-8.5V4.5Zm4 4h.01',
  route: 'M6 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm12-10a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM6 15V9a4 4 0 0 1 4-4h4M18 9v6a4 4 0 0 1-4 4h-4',
  chart: 'M4 20V4m0 16h16M8 16v-4m4 4V8m4 8v-6',
  bolt: 'M13 3 5 13.5h6L10 21l8-10.5h-6L13 3Z',
  play: 'M8 5.5v13l11-6.5-11-6.5Z',
  clock: 'M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm0-12v4.5l3 2',
  sun: 'M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0-12.5V5m0 14v1.5M3.5 12H5m14 0h1.5M6 6l1 1m10 10 1 1M6 18l1-1M17 7l1-1',
  moon: 'M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z',
  copy: 'M8 8.5h10v11H8v-11Zm-3 7H4V4.5h10v1',
  youtube: 'M3 7.5a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3v-9Zm7 1.5v6l5.5-3L10 9Z',
};

export function Icon({
  d,
  size = 16,
  stroke = 1.6,
  className,
}: {
  d: string;
  size?: number;
  stroke?: number;
  className?: string;
}) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={{ maxWidth: 'none' }}
    >
      <path d={ICONS[d] || d} />
    </svg>
  );
}

/** Logo JudolGuard: perisai dengan tanda centang di dalam kotak lembut. */
export function Mark({ size = 26 }: { size?: number }) {
  return (
    <svg
      className="msp-mark"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      style={{ maxWidth: 'none' }}
    >
      <rect width="24" height="24" rx="7" fill="var(--msp-ink)" />
      <path
        d="M12 4.8 17.8 7v4.4c0 3.7-2.5 6.4-5.8 7.5-3.3-1.1-5.8-3.8-5.8-7.5V7L12 4.8Z"
        fill="var(--msp-paper)"
      />
      <path
        d="m9.4 12.1 1.8 1.8 3.6-3.7"
        fill="none"
        stroke="var(--msp-ink)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Bud() {
  return (
    <svg className="msp-bud" width="10" height="10" viewBox="0 0 10 10" aria-hidden="true" style={{ maxWidth: 'none' }}>
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <ellipse
          key={i}
          cx="5"
          cy="2.3"
          rx="1.3"
          ry="2.2"
          fill="currentColor"
          opacity=".55"
          transform={`rotate(${i * 60} 5 5)`}
        />
      ))}
      <circle cx="5" cy="5" r="1.5" fill="currentColor" />
    </svg>
  );
}

export function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="msp-eyebrow">
      <Bud />
      {children}
    </p>
  );
}

/** Judul serif Newsreader dua nada: baris pertama pekat, baris kedua lembut. */
export function Title({
  text,
  as = 'h2',
  className,
  id,
}: {
  text: string;
  as?: 'h1' | 'h2' | 'h3';
  className?: string;
  id?: string;
}) {
  const [first, ...rest] = text.split('\n');
  const Tag = as;
  return (
    <Tag className={'msp-title' + (className ? ' ' + className : '')} id={id}>
      <span className="msp-title-a">{first}</span>
      {rest.length > 0 && (
        <>
          {' '}
          <span className="msp-title-b">{rest.join(' ')}</span>
        </>
      )}
    </Tag>
  );
}

export function Avatar({ name, size = 28, brand }: { name: string; size?: number; brand?: boolean }) {
  if (brand) {
    return (
      <span className="msp-avatar msp-avatar-brand" style={{ width: size, height: size }} aria-hidden="true">
        <Mark size={size} />
      </span>
    );
  }
  const h = hueOf(name);
  return (
    <span
      className="msp-avatar"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.38,
        background: `hsl(${h} 38% 88%)`,
        color: `hsl(${h} 32% 30%)`,
      }}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  );
}

export function Button({
  children,
  onClick,
  variant = 'solid',
  className,
  type = 'button',
  disabled,
  arrow,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'solid' | 'ghost' | 'line';
  className?: string;
  type?: 'button' | 'submit';
  disabled?: boolean;
  arrow?: boolean;
}) {
  return (
    <button
      type={type}
      className={`msp-btn msp-btn-${variant}` + (className ? ' ' + className : '')}
      onClick={onClick}
      disabled={disabled}
    >
      <span>{children}</span>
      {arrow && <Icon d="arrow" size={15} className="msp-btn-arrow" />}
    </button>
  );
}

export type ZoneType = 'judol' | 'review' | 'bukan';

/** Badge zona klasifikasi menggunakan sistem chip Mallow. */
export function ZoneChip({ zone, score, ruleHit }: { zone: ZoneType; score?: string; ruleHit?: boolean }) {
  // Pemetaan ke data-st bawaan CSS template:
  // reading/drafting = amber (warn), handed = purple/rose, resolved = green (good)
  const st = zone === 'bukan' ? 'resolved' : zone === 'review' ? 'drafting' : 'handed';
  const label =
    zone === 'judol'
      ? `Judol${score ? ' · ' + score : ''}`
      : zone === 'review'
        ? `Review${ruleHit ? ' (Aturan)' : score ? ' · ' + score : ''}`
        : `Aman${score ? ' · ' + score : ''}`;
  return (
    <span className="msp-chip" data-st={st}>
      {label}
    </span>
  );
}

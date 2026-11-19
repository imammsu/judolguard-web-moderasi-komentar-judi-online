import * as React from 'react';

import { PaintCtx } from './meadow-canvas';

/** Apakah pengguna meminta gerakan dikurangi (dibagikan lewat PaintCtx). */
export function useReduced() {
  const env = React.useContext(PaintCtx);
  return env ? env.reduced : false;
}

/**
 * Tahap animasi yang maju sendiri setiap `play` berubah:
 * 0 -> count, jeda `gap` ms antar tahap. Bila gerakan dikurangi, langsung ke akhir.
 */
export function useStages(play: number, count: number, gap: number) {
  const reduced = useReduced();
  const [stage, setStage] = React.useState(0);
  React.useEffect(() => {
    if (!play) return;
    if (reduced) {
      setStage(count);
      return;
    }
    setStage(0);
    const ids: number[] = [];
    for (let i = 1; i <= count; i++) {
      ids.push(window.setTimeout(() => setStage(i), 350 + gap * (i - 1)));
    }
    return () => ids.forEach((id) => window.clearTimeout(id));
  }, [play, count, gap, reduced]);
  return stage;
}

/** Salin teks ke clipboard dengan umpan balik "tersalin" sesaat. */
export function useCopy() {
  const [copied, setCopied] = React.useState(false);
  const timer = React.useRef(0);
  const copy = React.useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    setCopied(true);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopied(false), 1800);
  }, []);
  return { copied, copy };
}

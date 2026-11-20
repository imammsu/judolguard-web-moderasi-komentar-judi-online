import * as React from 'react';

import {
  FaqSection,
  FeatureStorySection,
  FooterSection,
  PlatformTourSection,
  SecuritySection,
  WaysSection,
} from '../components/landing/ContentSections';
import { LandingCtx } from '../components/landing/ctx';
import { LandingHero, LandingNav } from '../components/landing/HeroSection';
import '../components/landing/judol-landing.css';
import { PALETTES, PaintCtx, useReducedMotion } from '../components/landing/meadow-canvas';
import { useAuth } from '../hooks/useAuth';
import { useAppearance } from '../theme/useAppearance';

const EMPTY_IMAGES: Record<string, string> = {};

export default function JudolLandingPage() {
  const { user, loading: authLoading, login, logout } = useAuth();
  const reduced = useReducedMotion();
  const { palette, setPalette, dark, toggleDark } = useAppearance();
  const root = React.useRef<HTMLDivElement | null>(null);

  const tokens = React.useMemo(() => {
    const group = PALETTES[palette] || PALETTES.meadow;
    return dark ? group.dark : group.light;
  }, [palette, dark]);

  const go = React.useCallback(
    (id: string) => {
      const el = root.current;
      if (!el) return;
      const target = el.querySelector(`[data-sec="${id}"]`) || el.querySelector(`#${id}`);
      if (target) {
        target.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
      }
    },
    [reduced],
  );

  // Animasi muncul halus (.msp-rise) saat seksi masuk ke viewport
  React.useEffect(() => {
    const el = root.current;
    if (!el || typeof IntersectionObserver !== 'function') return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.setAttribute('data-in', '');
            io.unobserve(e.target);
          }
        }
      },
      { rootMargin: '0px 0px -8% 0px' },
    );
    el.querySelectorAll('.msp-rise').forEach((n) => io.observe(n));
    el.setAttribute('data-ready', '');
    return () => io.disconnect();
  }, []);

  const paintEnv = React.useMemo(
    () => ({
      paint: tokens.paint,
      dark,
      reduced,
      seed: 0,
      images: EMPTY_IMAGES,
    }),
    [tokens.paint, dark, reduced],
  );

  const landingEnv = React.useMemo(
    () => ({
      user,
      authLoading,
      login,
      logout,
      go,
      palette,
      setPalette,
      dark,
       toggleDark,
    }),
    [user, authLoading, login, logout, go, palette, setPalette, dark, toggleDark],
  );

  const vars = {
    '--msp-h': '100svh',
    '--msp-paper': tokens.paper,
    '--msp-soft': tokens.soft,
    '--msp-card': tokens.card,
    '--msp-ink': tokens.ink,
    '--msp-muted': tokens.muted,
    '--msp-rule': tokens.rule,
    '--msp-button': tokens.button,
    '--msp-button-ink': tokens.buttonInk,
    '--msp-good': tokens.good,
    '--msp-warn': tokens.warn,
    '--msp-hand': tokens.hand,
    '--msp-sky': tokens.paint.sky[1],
    '--msp-grass': tokens.paint.grass[2],
  } as React.CSSProperties;

  return (
    <PaintCtx.Provider value={paintEnv}>
      <LandingCtx.Provider value={landingEnv}>
        <div
          ref={root}
          className="msp-root"
          data-theme={dark ? 'dark' : 'light'}
          data-reduced={reduced ? '' : undefined}
          style={vars}
        >
          <LandingNav />
          <main>
            <LandingHero />
            <WaysSection />
            <FeatureStorySection />
            <PlatformTourSection />
            <SecuritySection />
            <FaqSection />
          </main>
          <FooterSection />
        </div>
      </LandingCtx.Provider>
    </PaintCtx.Provider>
  );
}

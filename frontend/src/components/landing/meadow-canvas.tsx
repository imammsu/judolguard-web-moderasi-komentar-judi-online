// Mesin kanvas latar "AI Shield & Studio Waves" untuk landing page JudolGuard.
// Menggambar gradient mesh modern, dot-grid halus, gelombang pelindung AI (shield waves),
// dan node sinyal bercahaya yang bergerak lembut serta merespons gerakan kursor.
import * as React from 'react';

export type MspScene =
  | 'hero'
  | 'resolve'
  | 'learn'
  | 'escalate'
  | 'smarter'
  | 'voice'
  | 'overnight'
  | 'platform'
  | 'pricing'
  | 'story'
  | 'cta';

export type MspPaint = {
  sky: string[];
  cloud: string;
  grass: string[];
  petal: string;
  shade: string;
  eye: string[];
  warm: string;
};

export type MspTokens = {
  paper: string;
  soft: string;
  card: string;
  ink: string;
  muted: string;
  rule: string;
  button: string;
  buttonInk: string;
  good: string;
  warn: string;
  hand: string;
  paint: MspPaint;
};

/* ---------- Palet Bertema Studio Modern & AI Shield ---------- */

// Palet 1: Indigo Shield (Modern AI SaaS - Slate, Indigo & Soft Violet)
const INDIGO_THEME: { light: MspTokens; dark: MspTokens } = {
  light: {
    paper: '#f8fafc',
    soft: '#eef2f7',
    card: '#ffffff',
    ink: '#0f172a',
    muted: '#475569',
    rule: 'rgba(15,23,42,.09)',
    button: '#1e1b4b',
    buttonInk: '#f8fafc',
    good: '#059669',
    warn: '#d97706',
    hand: '#e11d48',
    paint: {
      sky: ['#e0e7ff', '#c7d2fe', '#6366f1'],
      cloud: '#ffffff',
      grass: ['#1e1b4b', '#312e81', '#4f46e5', '#a5b4fc'],
      petal: '#ffffff',
      shade: '#94a3b8',
      eye: ['#4f46e5', '#818cf8'],
      warm: '#f43f5e',
    },
  },
  dark: {
    paper: '#090d16',
    soft: '#111827',
    card: '#172033',
    ink: '#f1f5f9',
    muted: '#94a3b8',
    rule: 'rgba(241,245,249,.1)',
    button: '#f1f5f9',
    buttonInk: '#0f172a',
    good: '#34d399',
    warn: '#fbbf24',
    hand: '#fb7185',
    paint: {
      sky: ['#312e81', '#1e1b4b', '#090d16'],
      cloud: '#6366f1',
      grass: ['#090d16', '#1e1b4b', '#3730a3', '#6366f1'],
      petal: '#e0e7ff',
      shade: '#475569',
      eye: ['#6366f1', '#a5b4fc'],
      warm: '#f43f5e',
    },
  },
};

// Palet 2: Creator Crimson (Terinspirasi YouTube Studio - Warm White, Rose & Violet)
const STUDIO_THEME: { light: MspTokens; dark: MspTokens } = {
  light: {
    ...INDIGO_THEME.light,
    paper: '#faf8f9',
    soft: '#f3eef1',
    ink: '#18131a',
    muted: '#635868',
    rule: 'rgba(24,19,26,.09)',
    button: '#261829',
    good: '#059669',
    hand: '#e11d48',
    paint: {
      sky: ['#ffe4e6', '#DDD6FE', '#7c3aed'],
      cloud: '#fff5f7',
      grass: ['#2e1065', '#581c87', '#9333ea', '#f43f5e'],
      petal: '#fff1f2',
      shade: '#c4b5fd',
      eye: ['#e11d48', '#fb7185'],
      warm: '#f43f5e',
    },
  },
  dark: {
    ...INDIGO_THEME.dark,
    paper: '#110d14',
    soft: '#1a1420',
    card: '#231b2b',
    ink: '#f5f0f7',
    muted: '#a89bb0',
    hand: '#fb7185',
    paint: {
      sky: ['#4c1d95', '#2e1065', '#110d14'],
      cloud: '#a855f7',
      grass: ['#110d14', '#2e1065', '#6b21a8', '#e11d48'],
      petal: '#fce7f3',
      shade: '#7e22ce',
      eye: ['#e11d48', '#fda4af'],
      warm: '#f43f5e',
    },
  },
};

// Palet 3: Cyber Teal (Clean Emerald & Cyan Tech Shield)
const CYBER_THEME: { light: MspTokens; dark: MspTokens } = {
  light: {
    ...INDIGO_THEME.light,
    paper: '#f7faf9',
    soft: '#ebf2f0',
    ink: '#0f1f1c',
    muted: '#4b635e',
    rule: 'rgba(15,31,28,.09)',
    button: '#112a26',
    good: '#059669',
    hand: '#e11d48',
    paint: {
      sky: ['#ccfbf1', '#bae6fd', '#0284c7'],
      cloud: '#f0fdfa',
      grass: ['#064e3b', '#0f766e', '#0d9488', '#38bdf8'],
      petal: '#f0fdfa',
      shade: '#7dd3fc',
      eye: ['#0284c7', '#38bdf8'],
      warm: '#14b8a6',
    },
  },
  dark: {
    ...INDIGO_THEME.dark,
    paper: '#081210',
    soft: '#0f1f1c',
    card: '#162b27',
    ink: '#ecfdf5',
    muted: '#86a8a0',
    hand: '#fb7185',
    paint: {
      sky: ['#0f766e', '#115e59', '#081210'],
      cloud: '#2dd4bf',
      grass: ['#081210', '#064e3b', '#0d9488', '#38bdf8'],
      petal: '#ccfbf1',
      shade: '#0284c7',
      eye: ['#0ea5e9', '#5eead4'],
      warm: '#14b8a6',
    },
  },
};

const PALETTES: Record<string, { light: MspTokens; dark: MspTokens }> = {
  meadow: INDIGO_THEME,
  lavender: STUDIO_THEME,
  harvest: CYBER_THEME,
};

/* ---------- Utilitas Matematika ---------- */

function rng(seed: number) {
  let s = (Math.floor(seed) * 2654435761) >>> 0 || 1;
  return () => {
    s ^= s << 13;
    s >>>= 0;
    s ^= s >> 17;
    s ^= s << 5;
    s >>>= 0;
    return s / 4294967296;
  };
}

function clamp(v: number, a: number, b: number) {
  return v < a ? a : v > b ? b : v;
}

type RGB = number[];

type Composition = {
  seed: number;
  waveCount: number;
  orbBias: number;
};

const SCENES: Record<string, Composition> = {
  hero: { seed: 3, waveCount: 5, orbBias: 0.25 },
  resolve: { seed: 11, waveCount: 3, orbBias: 0.45 },
  learn: { seed: 19, waveCount: 4, orbBias: 0.65 },
  escalate: { seed: 27, waveCount: 3, orbBias: 0.35 },
  smarter: { seed: 9, waveCount: 4, orbBias: 0.55 },
  voice: { seed: 17, waveCount: 4, orbBias: 0.3 },
  overnight: { seed: 21, waveCount: 4, orbBias: 0.7 },
  platform: { seed: 5, waveCount: 5, orbBias: 0.5 },
  pricing: { seed: 33, waveCount: 3, orbBias: 0.4 },
  story: { seed: 41, waveCount: 3, orbBias: 0.6 },
  cta: { seed: 45, waveCount: 4, orbBias: 0.5 },
};

function hexRgb(c: string): RGB {
  const h = c.replace('#', '');
  const f =
    h.length === 3
      ? h
          .split('')
          .map((x) => x + x)
          .join('')
      : h;
  return [
    parseInt(f.slice(0, 2), 16) || 0,
    parseInt(f.slice(2, 4), 16) || 0,
    parseInt(f.slice(4, 6), 16) || 0,
  ];
}

function mixRgb(a: RGB, b: RGB, t: number): RGB {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

function css(c: RGB, a: number) {
  return `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a.toFixed(3)})`;
}

function offscreen(w: number, h: number, s: number) {
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(w * s));
  c.height = Math.max(1, Math.round(h * s));
  const x = c.getContext('2d') as CanvasRenderingContext2D;
  x.scale(s, s);
  return { c, x };
}

/**
 * Menggambar latar bertema AI Shield & Digital Studio dalam 2 layer:
 * - `back`: gradient mesh modern, cahaya ambient radial, dan dot-grid teknologi halus.
 * - `front`: gelombang pelindung (shield waves), cincin radar halus, dan node sinyal
 *   yang bergerak lembut serta merespons sentuhan kursor.
 */
function paintStudioBackdrop(
  W: number,
  H: number,
  pad: number,
  S: Composition,
  paint: MspPaint,
  dark: boolean,
  seedShift: number,
) {
  const r = rng(S.seed * 7919 + seedShift * 104729 + 31);
  const sky = paint.sky.map(hexRgb);
  const tones = paint.grass.map(hexRgb);
  const highlight = hexRgb(paint.cloud);
  const accent = hexRgb(paint.warm);
  const nodeColor = hexRgb(paint.eye[1]);

  // 1. LAYER BELAKANG (Statis: Gradient Mesh + Ambient Glow + Dot Grid)
  const back = offscreen(W, H, 1);
  const bx = back.x;
  {
    const g = bx.createLinearGradient(0, 0, W * 0.9, H);
    if (dark) {
      g.addColorStop(0, css(tones[0], 1));
      g.addColorStop(0.5, css(tones[1], 1));
      g.addColorStop(1, css(mixRgb(tones[2], sky[0], 0.4), 1));
    } else {
      g.addColorStop(0, css(mixRgb(sky[0], highlight, 0.35), 1));
      g.addColorStop(0.55, css(sky[1], 1));
      g.addColorStop(1, css(mixRgb(sky[2], tones[2], 0.35), 1));
    }
    bx.fillStyle = g;
    bx.fillRect(0, 0, W, H);

    // Cahaya ambient radial (orb mesh)
    const orbs = [
      { x: W * (0.2 + S.orbBias * 0.4), y: H * 0.25, rad: Math.max(W, H) * 0.55, col: sky[2], al: dark ? 0.28 : 0.32 },
      { x: W * 0.82, y: H * 0.75, rad: Math.max(W, H) * 0.5, col: accent, al: dark ? 0.22 : 0.24 },
      { x: W * 0.15, y: H * 0.85, rad: Math.max(W, H) * 0.45, col: tones[2], al: dark ? 0.3 : 0.28 },
    ];
    for (const o of orbs) {
      const rg = bx.createRadialGradient(o.x, o.y, 0, o.x, o.y, o.rad);
      rg.addColorStop(0, css(o.col, o.al));
      rg.addColorStop(1, css(o.col, 0));
      bx.fillStyle = rg;
      bx.fillRect(0, 0, W, H);
    }

    // Dot-matrix grid teknologi halus
    const step = Math.max(22, Math.round(Math.min(W, H) / 18));
    bx.fillStyle = dark ? css(highlight, 0.08) : css(tones[0], 0.08);
    for (let gx = step; gx < W; gx += step) {
      for (let gy = step; gy < H; gy += step) {
        bx.beginPath();
        bx.arc(gx, gy, 1.1, 0, Math.PI * 2);
        bx.fill();
      }
    }
  }

  // 2. LAYER DEPAN (Bergerak: Gelombang AI Shield, Garis Sinyal, & Partikel Bercahaya)
  const FW = W + pad * 2;
  const front = offscreen(FW, H, 1);
  const fx = front.x;
  {
    // Gelombang pita cahaya (AI Filter Waves)
    const waves = S.waveCount + 1;
    for (let w = 0; w < waves; w++) {
      const t = w / Math.max(1, waves - 1);
      const baseY = H * (0.28 + t * 0.54);
      const amp = H * (0.06 + r() * 0.08);
      const freq = (1.4 + r() * 1.2) * Math.PI * 2;
      const phase = r() * Math.PI * 2;
      const waveCol = w % 2 === 0 ? mixRgb(tones[2], sky[2], 0.5) : mixRgb(accent, sky[2], 0.55);

      const wg = fx.createLinearGradient(0, baseY - amp, 0, H);
      wg.addColorStop(0, css(waveCol, dark ? 0.24 : 0.22));
      wg.addColorStop(1, css(tones[1], dark ? 0.04 : 0.03));

      fx.fillStyle = wg;
      fx.beginPath();
      fx.moveTo(0, H);
      for (let x = 0; x <= FW; x += 12) {
        const nx = x / FW;
        const y =
          baseY +
          Math.sin(nx * freq + phase) * amp +
          Math.cos(nx * freq * 0.5 - phase) * (amp * 0.45);
        fx.lineTo(x, y);
      }
      fx.lineTo(FW, H);
      fx.closePath();
      fx.fill();

      // Garis tepi atas gelombang bercahaya
      fx.strokeStyle = css(highlight, dark ? 0.22 : 0.45);
      fx.lineWidth = 1.4;
      fx.beginPath();
      for (let x = 0; x <= FW; x += 10) {
        const nx = x / FW;
        const y =
          baseY +
          Math.sin(nx * freq + phase) * amp +
          Math.cos(nx * freq * 0.5 - phase) * (amp * 0.45);
        if (x === 0) fx.moveTo(x, y);
        else fx.lineTo(x, y);
      }
      fx.stroke();
    }

    // Busur lingkaran pelindung (Shield Radar Arcs)
    const arcX = FW * (0.18 + S.orbBias * 0.6);
    const arcY = H * 0.22;
    for (let i = 1; i <= 3; i++) {
      const rad = Math.min(W, H) * (0.18 * i);
      fx.strokeStyle = css(highlight, dark ? 0.1 : 0.26);
      fx.lineWidth = 1;
      fx.setLineDash([5, 7]);
      fx.beginPath();
      fx.arc(arcX, arcY, rad, 0, Math.PI * 2);
      fx.stroke();
    }
    fx.setLineDash([]);

    // Node sinyal & kartu mikro abstrak yang melayang
    const nodeCount = 14;
    for (let i = 0; i < nodeCount; i++) {
      const nx = pad + r() * W;
      const ny = H * (0.12 + r() * 0.76);
      const rad = 3 + r() * 4.5;
      const isAccent = i % 3 === 0;
      const c = isAccent ? accent : nodeColor;

      // Glow di sekitar node
      const ng = fx.createRadialGradient(nx, ny, 0, nx, ny, rad * 4.5);
      ng.addColorStop(0, css(c, dark ? 0.45 : 0.38));
      ng.addColorStop(1, css(c, 0));
      fx.fillStyle = ng;
      fx.beginPath();
      fx.arc(nx, ny, rad * 4.5, 0, Math.PI * 2);
      fx.fill();

      // Inti node
      fx.fillStyle = css(highlight, 0.9);
      fx.beginPath();
      fx.arc(nx, ny, rad * 0.7, 0, Math.PI * 2);
      fx.fill();
    }
  }

  return { back: back.c, front: front.c };
}

type Painter = {
  canvas: HTMLCanvasElement;
  scene: Composition;
  paint: MspPaint;
  dark: boolean;
  seed: number;
  w: number;
  h: number;
  scale: number;
  visible: boolean;
  still: boolean;
  layers: { back: HTMLCanvasElement; front: HTMLCanvasElement } | null;
  key: string;
  pad: number;
  phase: number;
  push: number;
  queued: boolean;
  dead: boolean;
};

const painters: Painter[] = [];
const queue: Painter[] = [];
let queueTimer = 0;
let rafId = 0;
let lastFrame = 0;

function enqueue(p: Painter) {
  if (p.queued || p.dead) return;
  p.queued = true;
  queue.push(p);
  if (!queueTimer) queueTimer = window.setTimeout(runQueue, 0);
}

function runQueue() {
  queueTimer = 0;
  queue.sort((a, b) => Number(b.visible) - Number(a.visible));
  const p = queue.shift();
  if (p) {
    p.queued = false;
    if (!p.dead && p.w > 0 && p.h > 0) {
      const key = `${p.w}x${p.h}:${JSON.stringify(p.paint)}${p.dark}${p.seed}`;
      if (key !== p.key) {
        const W = Math.round(p.w * p.scale);
        const H = Math.round(p.h * p.scale);
        p.pad = Math.round(W * 0.05);
        p.layers = paintStudioBackdrop(W, H, p.pad, p.scene, p.paint, p.dark, p.seed);
        p.canvas.width = W;
        p.canvas.height = H;
        p.key = key;
        p.canvas.setAttribute('data-painted', '');
        drawFrame(p, performance.now());
      }
    }
  }
  if (queue.length) queueTimer = window.setTimeout(runQueue, 16);
}

function drawFrame(p: Painter, t: number) {
  const L = p.layers;
  if (!L) return;
  const ctx = p.canvas.getContext('2d');
  if (!ctx) return;
  const W = p.canvas.width;
  const H = p.canvas.height;
  ctx.drawImage(L.back, 0, 0);
  if (p.still) {
    ctx.drawImage(L.front, -p.pad, 0);
    return;
  }
  const amp = W * 0.012;
  const band = Math.max(2, Math.round(3 * p.scale));
  const drift = 0.55 + 0.45 * Math.sin(t * 0.00037 + p.phase) * Math.sin(t * 0.00071 + p.phase * 2);
  for (let y = 0; y < H; y += band) {
    const f = Math.pow(1 - y / H, 1.2);
    const dx = amp * f * (Math.sin(t * 0.0014 + (y / H) * 2.8 + p.phase) * drift + p.push);
    ctx.drawImage(L.front, 0, y, L.front.width, band, dx - p.pad, y, L.front.width, band);
  }
}

function tick(t: number) {
  rafId = 0;
  let any = false;
  if (t - lastFrame > 30) {
    lastFrame = t;
    for (const p of painters) {
      if (!p.visible || p.still || !p.layers) continue;
      p.push *= 0.94;
      drawFrame(p, t);
    }
  }
  for (const p of painters) if (p.visible && !p.still) any = true;
  if (any && !document.hidden) rafId = requestAnimationFrame(tick);
}

function wake() {
  if (!rafId) rafId = requestAnimationFrame(tick);
}

/* ---------- Hooks ---------- */

function useReducedMotion() {
  const [reduced, setReduced] = React.useState(false);
  React.useEffect(() => {
    if (typeof matchMedia !== 'function') return;
    const mq = matchMedia('(prefers-reduced-motion: reduce)');
    const on = () => setReduced(mq.matches);
    on();
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  return reduced;
}

function useInView(ref: { current: Element | null }, margin = '0px', threshold = 0) {
  const [state, setState] = React.useState({ seen: false, now: false });
  React.useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver !== 'function') {
      setState({ seen: true, now: true });
      return;
    }
    const io = new IntersectionObserver(
      ([e]) => setState((s) => ({ seen: s.seen || e.isIntersecting, now: e.isIntersecting })),
      { rootMargin: margin, threshold },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [ref, margin, threshold]);
  return state;
}

function useTween(target: number, run: boolean, ms = 900) {
  const [v, setV] = React.useState(run ? 0 : target);
  const from = React.useRef(0);
  const cur = React.useRef(v);
  cur.current = v;
  React.useEffect(() => {
    if (!run) return;
    from.current = cur.current;
    const start = performance.now();
    let id = 0;
    const step = (t: number) => {
      const k = Math.min(1, (t - start) / ms);
      const e = 1 - Math.pow(1 - k, 3);
      setV(from.current + (target - from.current) * e);
      if (k < 1) id = requestAnimationFrame(step);
    };
    id = requestAnimationFrame(step);
    return () => cancelAnimationFrame(id);
  }, [target, run, ms]);
  return run ? v : target;
}

const PaintCtx = React.createContext<null | {
  paint: MspPaint;
  dark: boolean;
  reduced: boolean;
  seed: number;
  images: Record<string, string>;
}>(null);

/* ---------- Komponen Kanvas Latar ---------- */

type MeadowProps = {
  scene: MspScene;
  active?: boolean;
  label?: string;
  className?: string;
  image?: string;
  alt?: string;
};

function Meadow({ scene, active = true, label, className, image, alt }: MeadowProps) {
  const env = React.useContext(PaintCtx);
  const box = React.useRef<HTMLDivElement | null>(null);
  const cv = React.useRef<HTMLCanvasElement | null>(null);
  const painter = React.useRef<Painter | null>(null);
  const activeRef = React.useRef(active);
  activeRef.current = active;
  const [failed, setFailed] = React.useState(false);
  const photo = (image || (env && env.images[scene]) || '') as string;
  const usePhoto = !!photo && !failed;
  const paint = env ? env.paint : INDIGO_THEME.light.paint;
  const dark = env ? env.dark : false;
  const still = env ? env.reduced : false;
  const seed = env ? env.seed : 0;

  React.useEffect(() => setFailed(false), [photo]);

  React.useEffect(() => {
    if (usePhoto) return;
    const el = box.current;
    const c = cv.current;
    if (!el || !c) return;
    const p: Painter = {
      canvas: c,
      scene: SCENES[scene] || SCENES.hero,
      paint,
      dark,
      seed,
      w: 0,
      h: 0,
      scale: Math.min(typeof devicePixelRatio === 'number' ? devicePixelRatio : 1, 1.5),
      visible: false,
      still,
      layers: null,
      key: '',
      pad: 0,
      phase: (SCENES[scene] ? SCENES[scene].seed : 1) * 1.7,
      push: 0,
      queued: false,
      dead: false,
    };
    painter.current = p;
    painters.push(p);
    const size = () => {
      const r = el.getBoundingClientRect();
      const w = Math.round(r.width);
      const h = Math.round(r.height);
      if (!w || !h) return;
      const budget = 1500000;
      p.scale = Math.min(
        typeof devicePixelRatio === 'number' ? devicePixelRatio : 1,
        1.5,
        Math.sqrt(budget / (w * h)),
      );
      if (Math.abs(w - p.w) > 24 || Math.abs(h - p.h) > 24 || !p.layers) {
        p.w = w;
        p.h = h;
        if (p.visible || !p.layers) enqueue(p);
      }
    };
    const ro = typeof ResizeObserver === 'function' ? new ResizeObserver(size) : null;
    if (ro) ro.observe(el);
    size();
    const io =
      typeof IntersectionObserver === 'function'
        ? new IntersectionObserver(
            ([e]) => {
              p.visible = e.isIntersecting && activeRef.current;
              if (e.isIntersecting) {
                size();
                enqueue(p);
              }
              wake();
            },
            { rootMargin: '300px 0px' },
          )
        : null;
    if (io) io.observe(el);
    else {
      p.visible = activeRef.current;
      enqueue(p);
    }
    let lastX = -1;
    const move = (e: PointerEvent) => {
      if (lastX >= 0 && p.w) p.push = clamp(p.push + ((e.clientX - lastX) / p.w) * 5, -1.6, 1.6);
      lastX = e.clientX;
    };
    const leave = () => {
      lastX = -1;
    };
    el.addEventListener('pointermove', move);
    el.addEventListener('pointerleave', leave);
    return () => {
      p.dead = true;
      const i = painters.indexOf(p);
      if (i > -1) painters.splice(i, 1);
      const q = queue.indexOf(p);
      if (q > -1) queue.splice(q, 1);
      if (ro) ro.disconnect();
      if (io) io.disconnect();
      el.removeEventListener('pointermove', move);
      el.removeEventListener('pointerleave', leave);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [usePhoto, scene, JSON.stringify(paint), dark, seed]);

  React.useEffect(() => {
    const p = painter.current;
    if (!p) return;
    p.still = still;
    if (p.layers) drawFrame(p, performance.now());
    wake();
  }, [still]);

  React.useEffect(() => {
    const p = painter.current;
    if (!p || !box.current) return;
    const r = box.current.getBoundingClientRect();
    p.visible = active && r.bottom > -300 && r.top < innerHeight + 300;
    if (p.visible) enqueue(p);
    wake();
  }, [active]);

  const sky = paint.sky;
  const aria = label ? { role: 'img', 'aria-label': label } : { 'aria-hidden': true };
  return (
    <div
      ref={box}
      className={'msp-paint' + (className ? ' ' + className : '')}
      data-scene={scene}
      style={{
        background: `linear-gradient(155deg,${sky[dark ? 2 : 0]},${sky[1]} 50%,${paint.grass[2]})`,
      }}
      {...aria}
    >
      {usePhoto ? (
        <img
          className="msp-photo"
          src={photo}
          alt={alt || ''}
          draggable={false}
          loading="lazy"
          decoding="async"
          onError={() => setFailed(true)}
          style={{ maxWidth: 'none' }}
        />
      ) : (
        <canvas ref={cv} className="msp-canvas" style={{ maxWidth: 'none' }} />
      )}
    </div>
  );
}

function Scaled({
  design,
  fit,
  className,
  style,
  children,
}: {
  design: number;
  fit: number;
  className?: string;
  style?: React.CSSProperties;
  children: React.ReactNode;
}) {
  const ref = React.useRef<HTMLDivElement | null>(null);
  const [k, setK] = React.useState(0.8);
  React.useEffect(() => {
    const el = ref.current;
    const parent = el && el.parentElement;
    if (!el || !parent) return;
    const on = () => {
      const w = parent.getBoundingClientRect().width;
      if (w) setK((w * fit) / design);
    };
    on();
    const ro = typeof ResizeObserver === 'function' ? new ResizeObserver(on) : null;
    if (ro) ro.observe(parent);
    return () => {
      if (ro) ro.disconnect();
    };
  }, [design, fit]);
  return (
    <div
      ref={ref}
      className={'msp-scaled' + (className ? ' ' + className : '')}
      style={{ width: design, transform: `scale(${k.toFixed(4)})`, ...style }}
    >
      {children}
    </div>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export { Meadow, Scaled, PaintCtx, PALETTES, useReducedMotion, useInView, useTween, clamp, rng };

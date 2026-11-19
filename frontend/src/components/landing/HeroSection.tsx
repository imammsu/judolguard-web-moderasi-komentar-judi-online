import * as React from 'react';

import { LandingCtx, type PaletteName } from './ctx';
import { SAMPLE_COMMENTS, type SampleComment } from './data';
import { useReduced } from './hooks';
import { Meadow, Scaled, useInView } from './meadow-canvas';
import { Avatar, Button, Icon, Mark, Title, ZoneChip } from './primitives';
import { fmt, scoreText } from './utils';

const NAV_ITEMS = [
  {
    label: 'Fitur Utama',
    items: [
      {
        label: 'Scan & Klasifikasi Cepat',
        href: '#ways',
        text: 'Pindai ratusan komentar video YouTube dalam hitungan detik',
      },
      {
        label: 'Deteksi Samaran Huruf & Situs Baru',
        href: '#features',
        text: 'Kenali huruf bergaya, singkatan angka, dan promosi terselubung',
      },
      {
        label: 'Salin Kata Kunci ke YouTube Studio',
        href: '#features',
        text: 'Kumpulkan daftar nama situs spam siap tempel ke Blocked words',
      },
      {
        label: 'Chatbot Analisis Pelaku Spam',
        href: '#platform',
        text: 'Temukan akun paling sering nyepam & jam serangan ramai',
      },
    ],
  },
  { label: 'Cara Kerja', href: '#ways' },
  { label: 'Tur Aplikasi', href: '#platform' },
  { label: 'Keamanan', href: '#security' },
  { label: 'FAQ', href: '#faq' },
];

const PALETTE_LABELS: { id: PaletteName; label: string }[] = [
  { id: 'meadow', label: 'Indigo' },
  { id: 'lavender', label: 'Studio' },
  { id: 'harvest', label: 'Emerald' },
];

export function LandingNav() {
  const { user, login, logout, go, palette, setPalette, dark, toggleDark } = React.useContext(LandingCtx);
  const [scrolled, setScrolled] = React.useState(false);
  const [open, setOpen] = React.useState(-1);
  const [sheet, setSheet] = React.useState(false);
  const ref = React.useRef<HTMLElement | null>(null);
  const closeT = React.useRef(0);

  React.useEffect(() => {
    const onScroll = () => {
      const el = ref.current;
      if (!el) return;
      setScrolled(window.scrollY > 8);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  React.useEffect(() => {
    if (open < 0 && !sheet) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(-1);
        setSheet(false);
      }
    };
    const onAway = (e: PointerEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(-1);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onAway);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onAway);
    };
  }, [open, sheet]);

  const follow = (href?: string) => (e: React.MouseEvent) => {
    if (href && href.startsWith('#')) {
      e.preventDefault();
      setOpen(-1);
      setSheet(false);
      go(href.slice(1));
    } else if (!href) {
      e.preventDefault();
    }
  };

  const hold = (i: number) => {
    window.clearTimeout(closeT.current);
    setOpen(i);
  };
  const drop = () => {
    window.clearTimeout(closeT.current);
    closeT.current = window.setTimeout(() => setOpen(-1), 160);
  };

  return (
    <header ref={ref} className="msp-nav" data-scrolled={scrolled || sheet ? '' : undefined}>
      <div className="msp-wrap msp-nav-row">
        <a href="#top" className="msp-brand" onClick={follow('#top')} aria-label="JudolGuard, kembali ke atas">
          <Mark />
          <span>JudolGuard</span>
        </a>

        <nav className="msp-nav-links" aria-label="Navigasi utama">
          {NAV_ITEMS.map((it, i) =>
            it.items ? (
              <div
                key={it.label}
                className="msp-nav-item"
                onPointerEnter={(e) => e.pointerType === 'mouse' && hold(i)}
                onPointerLeave={(e) => e.pointerType === 'mouse' && drop()}
              >
                <button
                  type="button"
                  className="msp-nav-link"
                  aria-expanded={open === i}
                  aria-haspopup="true"
                  onClick={() => setOpen(open === i ? -1 : i)}
                >
                  {it.label}
                  <Icon d="down" size={13} className="msp-chev" />
                </button>
                <div className="msp-menu" data-open={open === i ? '' : undefined} role="menu" aria-label={it.label}>
                  <div className="msp-menu-list">
                    {it.items.map((s) => (
                      <a
                        key={s.label}
                        role="menuitem"
                        href={s.href}
                        onClick={follow(s.href)}
                        className="msp-menu-link"
                        tabIndex={open === i ? 0 : -1}
                      >
                        <b>{s.label}</b>
                        <span>{s.text}</span>
                      </a>
                    ))}
                  </div>
                  <a href="#top" className="msp-menu-feature" onClick={follow('#top')} tabIndex={open === i ? 0 : -1}>
                    <span className="msp-menu-art">{open === i && <Meadow scene="resolve" />}</span>
                    <b>Simulasi Moderasi 3 Zona</b>
                    <span>Klik komentar di layar atas untuk melihat cara AI memisahkan spam dan komentar asli.</span>
                  </a>
                </div>
              </div>
            ) : (
              <a key={it.label} className="msp-nav-link" href={it.href} onClick={follow(it.href)}>
                {it.label}
              </a>
            ),
          )}
        </nav>

        <div className="msp-nav-actions">
          <div className="msp-seg msp-login" role="radiogroup" aria-label="Tema warna">
            {PALETTE_LABELS.map((p) => (
              <button
                key={p.id}
                type="button"
                role="radio"
                aria-checked={palette === p.id}
                onClick={() => setPalette(p.id)}
              >
                {p.label}
              </button>
            ))}
          </div>

          <button
            type="button"
            className="msp-nav-link"
            onClick={toggleDark}
            aria-label={dark ? 'Gunakan mode terang' : 'Gunakan mode gelap'}
            title={dark ? 'Mode terang' : 'Mode gelap'}
          >
            <Icon d={dark ? 'sun' : 'moon'} size={15} />
          </button>

          {user ? (
            <>
              <span className="msp-nav-link msp-login" title={user.email}>
                {user.thumbnail_url ? (
                  <img
                    src={user.thumbnail_url}
                    alt={user.channel_title}
                    width={22}
                    height={22}
                    style={{ borderRadius: '50%' }}
                  />
                ) : (
                  <Avatar name={user.channel_title} size={22} />
                )}
                <b>{user.channel_title}</b>
              </span>
              <Button variant="line" onClick={() => { window.location.href = '/videos'; }} className="msp-nav-cta">
                Buka Video Channel
              </Button>
              <Button variant="line" onClick={logout} className="msp-nav-cta">
                Keluar
              </Button>
            </>
          ) : (
            <Button onClick={() => login('/videos')} className="msp-nav-cta" arrow>
              Masuk dengan YouTube
            </Button>
          )}

          <button
            type="button"
            className="msp-burger"
            aria-label={sheet ? 'Tutup menu' : 'Buka menu'}
            aria-expanded={sheet}
            onClick={() => setSheet(!sheet)}
          >
            <Icon d={sheet ? 'close' : 'menu'} size={20} />
          </button>
        </div>
      </div>

      <div className="msp-sheet" data-open={sheet ? '' : undefined} aria-hidden={!sheet}>
        <div className="msp-wrap">
          {NAV_ITEMS.map((it) => (
            <div key={it.label} className="msp-sheet-group">
              {it.items ? (
                <>
                  <p className="msp-sheet-head">{it.label}</p>
                  {it.items.map((s) => (
                    <a key={s.label} href={s.href} onClick={follow(s.href)} tabIndex={sheet ? 0 : -1}>
                      {s.label}
                    </a>
                  ))}
                </>
              ) : (
                <a href={it.href} onClick={follow(it.href)} tabIndex={sheet ? 0 : -1} className="msp-sheet-top">
                  {it.label}
                </a>
              )}
            </div>
          ))}
          <div className="msp-sheet-actions">
            <Button variant="line" onClick={toggleDark}>
              {dark ? 'Mode Terang' : 'Mode Gelap'}
            </Button>
            {user ? (
              <Button
                onClick={() => {
                  setSheet(false);
                  window.location.href = '/videos';
                }}
              >
                Buka Video Channel ({user.channel_title})
              </Button>
            ) : (
              <Button
                onClick={() => {
                  setSheet(false);
                  login('/videos');
                }}
              >
                Masuk dengan YouTube
              </Button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

/**
 * Simulasi Live Moderasi 3 Zona di dalam jendela Hero (ramah kreator, tanpa istilah teknis belakang layar).
 */
function JudolHeroApp({ live, narrow }: { live: boolean; narrow: boolean }) {
  const reduced = useReduced();
  const [auto, setAuto] = React.useState(true);
  const [zoneFilter, setZoneFilter] = React.useState<'all' | 'judol' | 'review' | 'bukan'>('all');
  const [list, setList] = React.useState<SampleComment[]>(() => SAMPLE_COMMENTS.slice(0, 6));
  const [selectedId, setSelectedId] = React.useState<string>(SAMPLE_COMMENTS[0].id);
  const [scannedCount, setScannedCount] = React.useState(1240);
  const cursor = React.useRef(6);

  const running = live && auto && !reduced;

  React.useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => {
      const nextItem = SAMPLE_COMMENTS[cursor.current % SAMPLE_COMMENTS.length];
      cursor.current += 1;
      const fresh: SampleComment = {
        ...nextItem,
        id: `${nextItem.id}-${cursor.current}`,
        ago: 'baru saja',
      };
      setList((prev) => [fresh, ...prev.slice(0, 6)]);
      setSelectedId(fresh.id);
      setScannedCount((c) => c + 1);
    }, 4800);
    return () => window.clearInterval(id);
  }, [running]);

  const filtered = zoneFilter === 'all' ? list : list.filter((c) => c.zone === zoneFilter);
  const current = filtered.find((c) => c.id === selectedId) || filtered[0] || list[0];

  const judolTotal = list.filter((c) => c.zone === 'judol').length + 39;
  const reviewTotal = list.filter((c) => c.zone === 'review').length + 6;
  const bukanTotal = scannedCount - judolTotal - reviewTotal;

  return (
    <div className="msp-app" data-narrow={narrow ? '' : undefined}>
      <div className="msp-app-bar">
        <span className="msp-app-dots" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        <span className="msp-app-ws">
          <Mark size={18} />
          Vlog Kuliner Malam Jogja
          <Icon d="down" size={12} />
        </span>
        <label className="msp-switch">
          <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
          <span className="msp-switch-track" aria-hidden="true">
            <span />
          </span>
          Simulasi Live
        </label>
        <span className="msp-app-search">
          <Icon d="search" size={13} />
          Cari isi komentar…
          <kbd>/</kbd>
        </span>
      </div>

      <div className="msp-app-body" data-narrow={narrow ? '' : undefined}>
        <aside className="msp-app-side" aria-label="Filter tiga zona">
          <p className="msp-app-label">Hasil Pemindaian</p>
          <button
            type="button"
            className="msp-side-row"
            data-on={zoneFilter === 'all' ? '' : undefined}
            onClick={() => setZoneFilter('all')}
          >
            <Icon d="inbox" size={14} />
            Semua Komentar
            <em>{fmt(scannedCount)}</em>
          </button>
          <button
            type="button"
            className="msp-side-row"
            data-on={zoneFilter === 'judol' ? '' : undefined}
            onClick={() => setZoneFilter('judol')}
          >
            <Icon d="shield" size={14} />
            Terdeteksi Judol
            <em>{judolTotal}</em>
          </button>
          <button
            type="button"
            className="msp-side-row"
            data-on={zoneFilter === 'review' ? '' : undefined}
            onClick={() => setZoneFilter('review')}
          >
            <Icon d="eye" size={14} />
            Perlu Review
            <em>{reviewTotal}</em>
          </button>
          <button
            type="button"
            className="msp-side-row"
            data-on={zoneFilter === 'bukan' ? '' : undefined}
            onClick={() => setZoneFilter('bukan')}
          >
            <Icon d="check" size={14} />
            Bukan Judol
            <em className="msp-count">{fmt(bukanTotal)}</em>
          </button>

          <p className="msp-app-label">Keamanan Moderasi</p>
          <span className="msp-side-row">
            <Icon d="bolt" size={14} />
            Kecepatan Scan
            <em>&lt; 2 dtk</em>
          </span>
          <span className="msp-side-row">
            <Icon d="hand" size={14} />
            Reject Otomatis
            <em>Nonaktif</em>
          </span>
          <span className="msp-side-row">
            <Icon d="tag" size={14} />
            Kata Kunci Blokir
            <em>8 ditemukan</em>
          </span>
        </aside>

        <div className="msp-app-list" role="listbox" aria-label="Daftar komentar video">
          <div className="msp-list-head">
            <b>Komentar Video</b>
            <span>{running ? 'Memindai live' : 'Dijeda'}</span>
          </div>
          {filtered.map((item) => (
            <button
              key={item.id}
              type="button"
              role="option"
              aria-selected={current && item.id === current.id}
              className="msp-row"
              onClick={() => setSelectedId(item.id)}
            >
              <Avatar name={item.author.replace('@', '')} size={26} />
              <span className="msp-row-main">
                <span className="msp-row-top">
                  <b>{item.author}</b>
                  <time>{item.ago}</time>
                </span>
                <span className="msp-row-sub">{item.textOriginal}</span>
              </span>
              <ZoneChip zone={item.zone} score={scoreText(item.score)} />
            </button>
          ))}
        </div>

        {current && (
          <section className="msp-app-convo" aria-label="Detail analisis komentar" aria-live="polite">
            <div className="msp-convo-head">
              <div>
                <b>{current.author}</b>
                <span>
                  <Icon d="youtube" size={12} />
                  Tingkat keyakinan AI: {scoreText(current.score)}
                </span>
              </div>
              <ZoneChip zone={current.zone} score={scoreText(current.score)} />
            </div>

            <div className="msp-bubble msp-bubble-in">
              <Avatar name={current.author.replace('@', '')} size={22} />
              <div>
                <span className="msp-bubble-who">Komentar di YouTube</span>
                <p>{current.textOriginal}</p>
              </div>
            </div>

            <div className="msp-bubble msp-bubble-out">
              <Avatar name="JudolGuard" brand size={22} />
              <div>
                <span className="msp-bubble-who">Alasan Deteksi AI</span>
                <p>
                  <b>{current.detectedPattern}</b>
                  <br />
                  <span style={{ fontSize: '11.5px', color: 'var(--msp-muted)' }}>{current.explanation}</span>
                </p>
              </div>
            </div>

            <div className="msp-outcome" data-st={current.zone === 'bukan' ? 'resolved' : 'handed'}>
              <Icon d={current.zone === 'bukan' ? 'check' : 'hand'} size={13} />
              {current.zone === 'judol'
                ? 'Disarankan untuk di-reject (menunggu konfirmasi Anda)'
                : current.zone === 'review'
                  ? 'Dipisahkan ke Perlu Review agar Anda periksa dulu'
                  : 'Komentar penonton asli — aman'}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

export function LandingHero() {
  const { user, login, go } = React.useContext(LandingCtx);
  const ref = React.useRef<HTMLDivElement | null>(null);
  const view = useInView(ref);
  const [wide, setWide] = React.useState(true);

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const onResize = () => setWide(el.getBoundingClientRect().width > 560);
    onResize();
    const ro = typeof ResizeObserver === 'function' ? new ResizeObserver(onResize) : null;
    if (ro) ro.observe(el);
    return () => {
      if (ro) ro.disconnect();
    };
  }, []);

  return (
    <section
      className="msp-hero"
      data-sec="top"
      style={{ minHeight: 'calc(min(100svh, 820px) - 68px)' }}
      aria-labelledby="msp-hero-title"
    >
      <div className="msp-wrap msp-hero-grid">
        <div className="msp-hero-copy">
          <button type="button" className="msp-badge msp-rise" onClick={() => go('features')}>
            <b>Moderasi AI</b>
            Deteksi komentar judi online YouTube dalam hitungan detik
            <Icon d="arrow" size={13} />
          </button>

          <Title
            as="h1"
            text={'Bersihkan komentar judol,\nkeputusan tetap di tangan Anda.'}
            className="msp-h1 msp-rise"
            id="msp-hero-title"
          />

          <p className="msp-lede msp-rise">
            Pilih video dari channel YouTube Anda dan tekan Scan. JudolGuard mengenali komentar promosi judi
            online—termasuk yang disamarkan dengan huruf bergaya atau singkatan—lalu mengelompokkannya ke tiga zona
            aman untuk Anda tinjau.
          </p>

          <div className="msp-hero-actions msp-rise">
            {user ? (
              <Button onClick={() => { window.location.href = '/videos'; }} arrow>
                Buka Video Channel: {user.channel_title}
              </Button>
            ) : (
              <Button onClick={() => login('/videos')} arrow>
                Hubungkan Channel YouTube
              </Button>
            )}
            <Button variant="ghost" onClick={() => go('ways')}>
              Lihat Cara Kerjanya
            </Button>
          </div>

          {/* <p className="msp-note msp-rise">
            Login resmi Google &amp; YouTube · Tanpa penghapusan otomatis · Dilengkapi daftar kata kunci blokir.
          </p> */}
        </div>

        <div className="msp-hero-art msp-rise" ref={ref}>
          <Meadow scene="hero" label="Latar visual gelombang pelindung AI JudolGuard" />
          <Scaled design={wide ? 900 : 400} fit={wide ? 1.0 : 0.86} className="msp-hero-window">
            <JudolHeroApp live={view.now} narrow={!wide} />
          </Scaled>
        </div>
      </div>
    </section>
  );
}

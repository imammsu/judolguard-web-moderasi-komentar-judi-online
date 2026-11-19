import * as React from 'react';

import { LandingCtx } from './ctx';
import {
  CHAT_PRESETS,
  EXTRACTED_KEYWORDS,
  FAQ_ITEMS,
  PLATFORM_TABS,
  SAMPLE_COMMENTS,
  SECURITY_ITEMS,
  type PlatformTourTab,
} from './data';
import { useCopy, useReduced, useStages } from './hooks';
import { Meadow, Scaled, useInView, useTween, type MspScene } from './meadow-canvas';
import { Avatar, Button, Eyebrow, Icon, Mark, Title, ZoneChip } from './primitives';
import { fmt, scoreText } from './utils';

/* =====================================================================
   1. TIGA TAHAP KERJA (#ways)
   ===================================================================== */

interface WayDef {
  scene: MspScene;
  kind: 'batch' | 'prepare' | 'human';
  title: string;
  text: string;
}

const WAY_DEFS: WayDef[] = [
  {
    scene: 'learn',
    kind: 'batch',
    title: '1. Pilih Video & Klik Scan',
    text: 'Pilih video dari daftar channel Anda lalu tekan Scan. Ratusan hingga ribuan komentar langsung dipindai sekaligus dalam hitungan detik.',
  },
  {
    scene: 'resolve',
    kind: 'prepare',
    title: '2. AI Mengenali Samaran Teks Spammer',
    text: 'Meskipun pelaku memakai huruf tebal unik (𝗚𝗔𝗖𝗢𝗥), spasi berjarak (g a c o r), angka pengganti huruf, atau nama situs baru, AI tetap dapat mengenalinya.',
  },
  {
    scene: 'escalate',
    kind: 'human',
    title: '3. Tinjau 3 Zona & Reject Sekaligus',
    text: 'Periksa hasil pengelompokan di zona Judol, Perlu Review, dan Bukan Judol. Ubah label bila ada yang keliru, lalu tolak seluruh spam sekaligus.',
  },
];

const SCAN_STEPS = [
  { icon: 'youtube', name: 'Ambil Komentar Video', meta: '1.240 komentar ditemukan' },
  { icon: 'spark', name: 'Baca Samaran Huruf', meta: 'Huruf unik & nama situs baru' },
  { icon: 'shield', name: 'Kelompokkan 3 Zona', meta: '42 Judol · 8 Review · 1.190 Aman' },
  { icon: 'tag', name: 'Siapkan Kata Kunci', meta: '8 situs & istilah siap salin' },
];

function WayVignette({ kind, play }: { kind: WayDef['kind']; play: number }) {
  const reduced = useReduced();
  const [pct, setPct] = React.useState(100);
  const stage = useStages(play, 3, 650);

  React.useEffect(() => {
    if (!play || kind !== 'batch') return;
    if (reduced) {
      setPct(100);
      return;
    }
    setPct(20);
    let v = 20;
    const id = window.setInterval(() => {
      v = Math.min(100, v + 5);
      setPct(v);
      if (v >= 100) window.clearInterval(id);
    }, 60);
    return () => window.clearInterval(id);
  }, [play, kind, reduced]);

  if (kind === 'batch') {
    return (
      <div className="msp-vig">
        <p className="msp-vig-head">
          <b>Memindai Komentar Video</b>
          <span>{pct >= 100 ? 'Selesai dalam 1,2 dtk' : `Memindai ${Math.floor(pct)}%`}</span>
        </p>
        {SCAN_STEPS.map((s, i) => {
          const done = pct >= (i + 1) * 25;
          const active = !done && pct >= i * 25;
          return (
            <div key={s.name} className="msp-src">
              <span className="msp-src-icon">
                <Icon d={s.icon} size={14} />
              </span>
              <span className="msp-src-main">
                <b>{s.name}</b>
                <span>{s.meta}</span>
              </span>
              <span className="msp-chip" data-st={done ? 'resolved' : active ? 'drafting' : 'queued'}>
                {done ? 'Selesai' : active ? 'Proses' : 'Menunggu'}
              </span>
            </div>
          );
        })}
        <span className="msp-meter" aria-hidden="true">
          <i style={{ width: `${pct}%` }} />
        </span>
      </div>
    );
  }

  if (kind === 'prepare') {
    return (
      <div className="msp-vig">
        <div className="msp-bubble msp-bubble-in">
          <Avatar name="sultan88" size={22} />
          <p>Main di 𝗚 𝗔 𝗖 𝗢 𝗥 77 pasti maxwin, WA 0812-3456-7890</p>
        </div>
        <div className="msp-bubble msp-bubble-out">
          <Avatar name="JudolGuard" brand size={22} />
          <p>Terdeteksi: samaran huruf berjarak, promosi situs judol, dan nomor kontak pendaftaran.</p>
        </div>
        <p className="msp-outcome" data-st="handed" data-show={stage >= 1 ? '' : undefined}>
          <Icon d="shield" size={13} />
          Keyakinan AI 99% → Masuk Zona Judol
        </p>
      </div>
    );
  }

  return (
    <div className="msp-vig">
      <div className="msp-bubble msp-bubble-in msp-seq" data-show={stage >= 1 ? '' : undefined}>
        <Avatar name="kreator" size={22} />
        <p>42 komentar di Zona Judol telah Anda tinjau dan pilih.</p>
      </div>
      <p className="msp-handoff" data-show={stage >= 2 ? '' : undefined}>
        <Icon d="hand" size={12} />
        Menunggu persetujuan Anda · Tidak ada reject otomatis
      </p>
      <div className="msp-bubble msp-bubble-in msp-bubble-agent msp-seq" data-show={stage >= 3 ? '' : undefined}>
        <Avatar name="JudolGuard" brand size={22} />
        <p>Selesai! 42 komentar spam telah disembunyikan dari video YouTube Anda.</p>
      </div>
    </div>
  );
}

function WayCard({ way }: { way: WayDef }) {
  const ref = React.useRef<HTMLElement | null>(null);
  const view = useInView(ref, '0px 0px -20% 0px');
  const [play, setPlay] = React.useState(0);

  React.useEffect(() => {
    if (view.seen) setPlay((p) => p || 1);
  }, [view.seen]);

  const replay = () => setPlay((p) => p + 1);

  return (
    <article
      ref={ref}
      className="msp-way msp-rise"
      onPointerEnter={(e) => e.pointerType === 'mouse' && replay()}
      onFocus={replay}
      tabIndex={0}
    >
      <div className="msp-way-art">
        <Meadow scene={way.scene} />
        <WayVignette kind={way.kind} play={play} />
      </div>
      <h3>{way.title}</h3>
      <p>{way.text}</p>
    </article>
  );
}

export function WaysSection() {
  return (
    <section className="msp-section" data-sec="ways" aria-labelledby="msp-ways-title">
      <div className="msp-wrap">
        <Eyebrow>Cara Kerja</Eyebrow>
        <Title
          text={'Tiga langkah praktis membersihkan\nkolom komentar channel Anda.'}
          className="msp-rise"
          id="msp-ways-title"
        />
        <div className="msp-ways">
          {WAY_DEFS.map((w) => (
            <WayCard key={w.kind} way={w} />
          ))}
        </div>
      </div>
    </section>
  );
}

/* =====================================================================
   2. STICKY SCROLL FEATURE STORY (#features)
   ===================================================================== */

const DETECTION_MODES = {
  smart: {
    accuracy: 98,
    newSites: 95,
    badge1: 'Komentar penonton asli tetap aman',
    badge2: 'Kenali situs yang baru ganti nama',
    bars: [92, 96, 95, 97, 98],
  },
  basic: {
    accuracy: 85,
    newSites: 62,
    badge1: 'Hanya mencocokkan kata lama',
    badge2: 'Mudah lolos saat huruf disamarkan',
    bars: [74, 65, 78, 70, 75],
  },
};

function sparkPath(values: number[], w: number, h: number) {
  if (!values.length) return '';
  const min = 55;
  const max = 100;
  const span = max - min;
  return values
    .map((v, i) => {
      const x = values.length === 1 ? w / 2 : (i / (values.length - 1)) * w;
      const y = h - ((v - min) / span) * h;
      return `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(' ');
}

function DetectionQualityCard() {
  const [mode, setMode] = React.useState<'smart' | 'basic'>('smart');
  const data = DETECTION_MODES[mode];
  const acc = useTween(data.accuracy, true, 650);
  const rec = useTween(data.newSites, true, 650);

  return (
    <div className="msp-card msp-fcard">
      <div className="msp-fcard-head">
        <b>Deteksi Samaran &amp; Situs Baru</b>
        <div className="msp-seg" role="radiogroup" aria-label="Perbandingan deteksi">
          <button
            type="button"
            role="radio"
            aria-checked={mode === 'smart'}
            onClick={() => setMode('smart')}
          >
            AI JudolGuard
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={mode === 'basic'}
            onClick={() => setMode('basic')}
          >
            Filter Biasa
          </button>
        </div>
      </div>

      <div className="msp-metrics">
        <div className="msp-metric">
          <span>
            <Icon d="shield" size={12} />
            Ketepatan Deteksi
          </span>
          <b>{Math.round(acc)}%</b>
          <em>{data.badge1}</em>
        </div>
        <div className="msp-metric">
          <span>
            <Icon d="spark" size={12} />
            Deteksi Situs Baru
          </span>
          <b>{Math.round(rec)}%</b>
          <em>{data.badge2}</em>
        </div>
      </div>

      <svg
        className="msp-spark"
        viewBox="0 0 240 46"
        preserveAspectRatio="none"
        aria-hidden="true"
        style={{ maxWidth: 'none' }}
      >
        <path
          d={`${sparkPath(data.bars, 240, 40)} L240 46 L0 46 Z`}
          className="msp-spark-fill"
          transform="translate(0 3)"
        />
        <path d={sparkPath(data.bars, 240, 40)} className="msp-spark-line" transform="translate(0 3)" />
      </svg>
    </div>
  );
}

function BlockedWordsCard() {
  const [selected, setSelected] = React.useState<string[]>(() =>
    EXTRACTED_KEYWORDS.slice(0, 5).map((k) => k.keyword),
  );
  const { copied, copy } = useCopy();

  const toggle = (kw: string) => {
    setSelected((prev) => (prev.includes(kw) ? prev.filter((x) => x !== kw) : [...prev, kw]));
  };

  const csvText = selected.join(', ');

  return (
    <div className="msp-card msp-fcard">
      <div className="msp-fcard-head">
        <b>Daftar Kata Kunci untuk YouTube Studio</b>
        <button
          type="button"
          className="msp-pill-btn"
          onClick={() => copy(csvText)}
          disabled={!selected.length}
        >
          <Icon d={copied ? 'check' : 'copy'} size={12} />
          {copied ? 'Tersalin!' : 'Salin Kata'}
        </button>
      </div>

      <div className="msp-chips" role="group" aria-label="Pilih kata kunci untuk disalin">
        {EXTRACTED_KEYWORDS.map((item) => {
          const active = selected.includes(item.keyword);
          return (
            <button
              key={item.keyword}
              type="button"
              aria-checked={active}
              onClick={() => toggle(item.keyword)}
            >
              {item.keyword} ({item.frequency}x)
            </button>
          );
        })}
      </div>

      <p
        className="msp-voice-text"
        style={{ minHeight: '64px', fontFamily: 'ui-monospace, monospace', fontSize: '12px' }}
      >
        {csvText || 'Klik kata kunci di atas untuk disalin ke YouTube Studio…'}
      </p>
    </div>
  );
}

function ChatbotPreviewCard() {
  const [presetId, setPresetId] = React.useState<string>(CHAT_PRESETS[0].id);
  const preset = CHAT_PRESETS.find((p) => p.id === presetId) || CHAT_PRESETS[0];

  return (
    <div className="msp-card msp-fcard">
      <div className="msp-voice-who">
        <Avatar name="JudolGuard" brand size={28} />
        <span>
          <b>Asisten Analisis Spam</b>
          <em>{preset.summaryLabel}</em>
        </span>
      </div>

      <div className="msp-chips" role="radiogroup" aria-label="Pertanyaan cepat">
        {CHAT_PRESETS.map((p) => (
          <button
            key={p.id}
            type="button"
            role="radio"
            aria-checked={preset.id === p.id}
            onClick={() => setPresetId(p.id)}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="msp-gaps">
        <p>{preset.answerTitle}</p>
        {preset.rows.map((r) => (
          <span key={r.col1}>
            <b>{r.col1}</b>
            <em>{r.badge}</em>
          </span>
        ))}
      </div>
    </div>
  );
}

const STORY_STEPS: {
  scene: MspScene;
  kind: 'metrics' | 'keywords' | 'chatbot';
  title: string;
  text: string;
}[] = [
  {
    scene: 'smarter',
    kind: 'metrics',
    title: 'Tetap mengenali spam meski pelaku terus berganti nama situs.',
    text: 'Filter kata biasa sering kebobolan saat spammer memakai huruf bergaya atau mengganti nama situs baru setiap minggu. AI JudolGuard membaca pola kalimat promosinya, sekaligus menjaga komentar penonton asli tetap aman.',
  },
  {
    scene: 'voice',
    kind: 'keywords',
    title: 'Kumpulkan nama situs spam untuk diblokir di YouTube Studio.',
    text: 'Tidak perlu menebak kata apa yang sedang dipakai spammer. JudolGuard merangkum daftar nama situs dan kata kunci yang paling sering muncul di komentar video Anda, siap disalin dalam format koma.',
  },
  {
    scene: 'overnight',
    kind: 'chatbot',
    title: 'Tanyakan siapa akun penyebar spam paling aktif di channel Anda.',
    text: 'Ingin tahu akun mana yang berkali-kali nyepam di banyak video atau jam berapa serangan spam paling ramai? Cukup klik pertanyaan cepat pada Asisten AI untuk melihat ringkasannya seketika.',
  },
];

function StoryCard({ kind }: { kind: (typeof STORY_STEPS)[number]['kind'] }) {
  if (kind === 'keywords') return <BlockedWordsCard />;
  if (kind === 'chatbot') return <ChatbotPreviewCard />;
  return <DetectionQualityCard />;
}

export function FeatureStorySection() {
  const { user, login } = React.useContext(LandingCtx);
  const [active, setActive] = React.useState(0);
  const steps = React.useRef<(HTMLElement | null)[]>([]);

  React.useEffect(() => {
    if (typeof IntersectionObserver !== 'function') return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) setActive(Number((e.target as HTMLElement).dataset.i));
        }
      },
      { rootMargin: '-45% 0px -45% 0px' },
    );
    steps.current.forEach((s) => s && io.observe(s));
    return () => io.disconnect();
  }, []);

  return (
    <section className="msp-section" data-sec="features" aria-labelledby="msp-features-title">
      <div className="msp-wrap">
        <Eyebrow>Keunggulan JudolGuard</Eyebrow>
        <Title
          text={'Moderasi lebih cerdas,\ntanpa ribet urusan teknis.'}
          className="msp-rise"
          id="msp-features-title"
        />

        <div className="msp-story">
          <div className="msp-story-stage" aria-hidden="true">
            {STORY_STEPS.map((f, i) => (
              <div key={f.kind} className="msp-stage-layer" data-on={active === i ? '' : undefined}>
                <Meadow scene={f.scene} active={active === i} />
                <div className="msp-stage-card">
                  <StoryCard kind={f.kind} />
                </div>
              </div>
            ))}
            <div className="msp-stage-dots">
              {STORY_STEPS.map((f, i) => (
                <i key={f.kind} data-on={active === i ? '' : undefined} />
              ))}
            </div>
          </div>

          <div className="msp-story-steps">
            {STORY_STEPS.map((f, i) => (
              <article
                key={f.kind}
                className="msp-step"
                data-i={i}
                data-on={active === i ? '' : undefined}
                ref={(el) => {
                  steps.current[i] = el;
                }}
              >
                <div className="msp-step-media">
                  <Meadow scene={f.scene} />
                  <div className="msp-stage-card">
                    <StoryCard kind={f.kind} />
                  </div>
                </div>
                <div className="msp-step-copy">
                  <span className="msp-step-n">{`0${i + 1}`}</span>
                  <h3>{f.title}</h3>
                  <p>{f.text}</p>
                  {!user && (
                    <Button variant="solid" onClick={login} arrow>
                      Hubungkan Channel YouTube
                    </Button>
                  )}
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* =====================================================================
   3. TUR LAYAR APLIKASI (#platform - 4 Tab)
   ===================================================================== */

const SAMPLE_VIDEOS = [
  { id: 'v1', title: 'Vlog Kuliner Malam Jogja — Gudeg & Bakmi Jawa', date: '14 Nov 2026', comments: 1240 },
  { id: 'v2', title: 'Rakit PC Gaming 8 Jutaan Terbaik 2026', date: '10 Nov 2026', comments: 980 },
  { id: 'v3', title: 'Tips Edit Video Cepat di Laptop Kentang', date: '04 Nov 2026', comments: 610 },
  { id: 'v4', title: 'Review Keyboard Mechanical Wireless Murah', date: '29 Okt 2026', comments: 430 },
];

function PlatformTourView({ kind }: { kind: PlatformTourTab['kind'] }) {
  if (kind === 'scan') {
    return (
      <div className="msp-pv">
        <div className="msp-kpis">
          <div>
            <span>Video Dipilih</span>
            <b>1.240</b>
            <em>komentar di YouTube</em>
          </div>
          <div>
            <span>Waktu Pemindaian</span>
            <b>~1,2s</b>
            <em>langsung dikelompokkan</em>
          </div>
          <div>
            <span>Status Moderasi</span>
            <b>Aman</b>
            <em>menunggu tinjauan Anda</em>
          </div>
        </div>
        <div className="msp-table" style={{ marginTop: '12px' }}>
          <div className="msp-tr msp-th">
            <span>Daftar Video Channel Anda</span>
            <span>Tanggal Tayang</span>
            <span>Jumlah Komentar</span>
            <span>Status</span>
            <span>Tindakan</span>
          </div>
          {SAMPLE_VIDEOS.map((v, i) => (
            <div key={v.id} className="msp-tr" style={{ animationDelay: `${i * 55}ms` }}>
              <span className="msp-td-main">
                <Avatar name={v.title} size={24} />
                <span>
                  <b>{v.title}</b>
                </span>
              </span>
              <span className="msp-mono">{v.date}</span>
              <span className="msp-mono">{fmt(v.comments)}</span>
              <span className="msp-tag">Siap Dipindai</span>
              <span className="msp-chip" data-st={i === 0 ? 'resolved' : 'queued'}>
                {i === 0 ? 'Scan Komentar' : 'Pilih Video'}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (kind === 'review') {
    return (
      <div className="msp-pv">
        <div className="msp-table">
          <div className="msp-tr msp-th">
            <span>Penulis &amp; Isi Komentar</span>
            <span>Kategori</span>
            <span>Keyakinan AI</span>
            <span>Deteksi</span>
            <span>Keputusan Kreator</span>
          </div>
          {SAMPLE_COMMENTS.slice(0, 6).map((c, i) => (
            <div key={c.id} className="msp-tr" style={{ animationDelay: `${i * 55}ms` }}>
              <span className="msp-td-main">
                <Avatar name={c.author.replace('@', '')} size={24} />
                <span>
                  <b>{c.author}</b>
                  <em>{c.textOriginal}</em>
                </span>
              </span>
              <ZoneChip zone={c.zone} />
              <span className="msp-conf">
                <i style={{ width: `${Math.max(8, Math.round(c.score * 46))}px` }} />
                {scoreText(c.score)}
              </span>
              <span className="msp-tag">
                {c.zone === 'judol' ? 'Promosi Situs' : c.zone === 'review' ? 'Pola Ajakan' : 'Penonton Asli'}
              </span>
              <span className="msp-mono">
                {c.zone === 'judol' ? 'Siap Di-reject' : c.zone === 'review' ? 'Periksa Dulu' : 'Biarkan Tampil'}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (kind === 'keywords') {
    return (
      <div className="msp-pv msp-pv-routing">
        <div className="msp-route-summary">
          <Icon d="spark" size={16} />
          <p>
            <b>Siap Ditempel ke YouTube Studio:</b> Centang nama situs dan kata promosi di bawah, lalu salin dalam
            format koma ke menu <i>Settings → Community → Blocked words</i>.
          </p>
        </div>
        <div className="msp-agents">
          {EXTRACTED_KEYWORDS.slice(0, 5).map((k, i) => (
            <div
              key={k.keyword}
              className="msp-agent"
              data-on={i < 3 ? '' : undefined}
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <Avatar name={k.keyword} size={28} />
              <div className="msp-agent-main">
                <b>{k.keyword}</b>
                <span className="msp-tags">
                  <i>{k.type === 'situs' ? 'Nama Situs' : 'Kata Promosi'}</i>
                  <i>Siap Disalin</i>
                </span>
              </div>
              <span className="msp-load" aria-label={`Frekuensi ${k.frequency}`}>
                <i style={{ width: `${Math.min(100, k.frequency * 3)}%` }} />
              </span>
              <em>{k.frequency}x ditemukan</em>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="msp-pv">
      <div className="msp-kpis">
        <div>
          <span>Topik Analisis</span>
          <b>7</b>
          <em>pertanyaan siap pakai</em>
        </div>
        <div>
          <span>Sumber Jawaban</span>
          <b>100%</b>
          <em>dari data video Anda</em>
        </div>
        <div>
          <span>Kecepatan</span>
          <b>Instan</b>
          <em>tanpa rekap manual</em>
        </div>
      </div>
      <div className="msp-report-row">
        <div className="msp-gaps">
          <p>Pertanyaan Populer Kreator</p>
          <span>
            <b>Akun mana yang paling sering spam?</b>
            <em>Daftar akun pelaku</em>
          </span>
          <span>
            <b>Berapa persen komentar judol di video ini?</b>
            <em>Ringkasan jumlah &amp; rasio</em>
          </span>
          <span>
            <b>Nama situs apa yang paling sering muncul?</b>
            <em>Top situs &amp; kata spam</em>
          </span>
          <span>
            <b>Jam berapa serangan spam paling ramai?</b>
            <em>Pola waktu serangan</em>
          </span>
        </div>
        <div className="msp-gaps">
          <p>Contoh Jawaban Asisten</p>
          {CHAT_PRESETS[0].rows.map((r) => (
            <span key={r.col1}>
              <b>{r.col1}</b>
              <em>{r.badge}</em>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export function PlatformTourSection() {
  const { user, login } = React.useContext(LandingCtx);
  const reduced = useReduced();
  const [tab, setTab] = React.useState(0);
  const [held, setHeld] = React.useState(false);
  const [manual, setManual] = React.useState(false);
  const ref = React.useRef<HTMLDivElement | null>(null);
  const view = useInView(ref);

  const auto = !manual && !held && !reduced && view.now;
  const cur = PLATFORM_TABS[tab];

  const pick = (i: number) => {
    setManual(true);
    setTab(i);
  };

  return (
    <section className="msp-section" data-sec="platform" aria-labelledby="msp-platform-title">
      <div className="msp-wrap">
        <Eyebrow>Tur Tampilan Aplikasi</Eyebrow>
        <Title
          text={'Satu dashboard rapi untuk memindai,\nmeninjau, dan memblokir spam.'}
          className="msp-rise"
          id="msp-platform-title"
        />

        <div
          className="msp-tour msp-rise"
          ref={ref}
          onPointerEnter={() => setHeld(true)}
          onPointerLeave={() => setHeld(false)}
          onFocusCapture={() => setHeld(true)}
          onBlurCapture={() => setHeld(false)}
        >
          <div className="msp-tabs" role="tablist" aria-label="Layar aplikasi JudolGuard">
            {PLATFORM_TABS.map((t, i) => (
              <button
                key={t.label}
                type="button"
                role="tab"
                id={`msp-tab-${i}`}
                aria-selected={tab === i}
                aria-controls="msp-tabpanel"
                tabIndex={tab === i ? 0 : -1}
                className="msp-tab"
                onClick={() => pick(i)}
                onKeyDown={(e) => {
                  if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                    e.preventDefault();
                    const n = (i + (e.key === 'ArrowRight' ? 1 : -1) + PLATFORM_TABS.length) % PLATFORM_TABS.length;
                    pick(n);
                    document.getElementById(`msp-tab-${n}`)?.focus();
                  }
                }}
              >
                <Icon d={t.icon} size={15} />
                {t.label}
                {tab === i && (
                  <span
                    className="msp-tab-progress"
                    data-run={auto ? '' : undefined}
                    onAnimationEnd={() => auto && setTab((tab + 1) % PLATFORM_TABS.length)}
                  />
                )}
              </button>
            ))}
          </div>

          <div className="msp-tour-body" role="tabpanel" id="msp-tabpanel" aria-labelledby={`msp-tab-${tab}`}>
            <div className="msp-tour-copy" key={`c-${tab}`}>
              <h3>{cur.title}</h3>
              <ul>
                {cur.points.map((p) => (
                  <li key={p.title}>
                    <span className="msp-tick">
                      <Icon d="check" size={13} stroke={2} />
                    </span>
                    <span>
                      <b>{p.title}</b>
                      {p.text}
                    </span>
                  </li>
                ))}
              </ul>
              <Button onClick={login} className="msp-wide" arrow>
                {user ? `Lanjutkan sebagai ${user.channel_title}` : 'Masuk dengan Akun YouTube'}
              </Button>
            </div>

            <div className="msp-tour-art">
              <Meadow scene="platform" />
              <Scaled design={760} fit={0.9} className="msp-tour-window">
                <div className="msp-app msp-app-tour">
                  <div className="msp-app-bar">
                    <span className="msp-app-dots" aria-hidden="true">
                      <i />
                      <i />
                      <i />
                    </span>
                    <span className="msp-app-ws">
                      <Mark size={18} />
                      JudolGuard · {cur.label}
                    </span>
                    <span className="msp-app-search">
                      <Icon d="search" size={13} />
                      Cari…
                    </span>
                  </div>
                  <div className="msp-tour-view" key={cur.kind}>
                    <PlatformTourView kind={cur.kind} />
                  </div>
                </div>
              </Scaled>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* =====================================================================
   4. KEAMANAN & PRIVASI KREATOR (#security)
   ===================================================================== */

export function SecuritySection() {
  return (
    <section className="msp-section msp-band" data-sec="security" aria-labelledby="msp-security-title">
      <div className="msp-wrap msp-center">
        <Eyebrow>Keamanan &amp; Kendali Kreator</Eyebrow>
        <Title
          text={'Aman untuk channel Anda,\npenuh di bawah kendali Anda.'}
          className="msp-rise"
          id="msp-security-title"
        />
        <p className="msp-sub msp-rise">
          JudolGuard dibangun mengikuti pedoman resmi YouTube agar Anda dapat memoderasi komentar dengan tenang tanpa
          risiko salah hapus.
        </p>

        <div className="msp-sec-grid">
          {SECURITY_ITEMS.map((s) => (
            <article key={s.title} className="msp-sec msp-rise">
              <span className="msp-sec-icon">
                <Icon d={s.icon} size={18} />
              </span>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/* =====================================================================
   5. PERTANYAAN UMUM / FAQ (#faq)
   ===================================================================== */

export function FaqSection() {
  const [open, setOpen] = React.useState(0);
  const half = Math.ceil(FAQ_ITEMS.length / 2);
  const cols = [FAQ_ITEMS.slice(0, half), FAQ_ITEMS.slice(half)];
  const uid = React.useId().replace(/:/g, '');

  return (
    <section className="msp-section msp-cta-sec" data-sec="faq" aria-labelledby="msp-faq-title">
      <div className="msp-wrap">
        <Eyebrow>Pertanyaan Umum</Eyebrow>
        <Title
          text={'Hal yang sering ditanyakan\noleh pemilik channel YouTube.'}
          className="msp-rise"
          id="msp-faq-title"
        />
        <div className="msp-faq">
          {cols.map((col, c) => (
            <div key={c} className="msp-faq-col msp-rise">
              {col.map((f, k) => {
                const i = c * half + k;
                const on = open === i;
                return (
                  <div key={f.q} className="msp-qa" data-open={on ? '' : undefined}>
                    <button
                      type="button"
                      aria-expanded={on}
                      aria-controls={`${uid}-a${i}`}
                      id={`${uid}-q${i}`}
                      onClick={() => setOpen(on ? -1 : i)}
                    >
                      {f.q}
                      <span className="msp-qa-icon" aria-hidden="true">
                        <Icon d="plus" size={16} />
                      </span>
                    </button>
                    <div className="msp-qa-a" id={`${uid}-a${i}`} role="region" aria-labelledby={`${uid}-q${i}`}>
                      <div>
                        <p>{f.a}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* =====================================================================
   6. FOOTER
   ===================================================================== */

const FOOTER_COLUMNS = [
  {
    title: 'Fitur Utama',
    links: [
      { label: 'Scan Komentar Video', href: '#ways' },
      { label: 'Deteksi Samaran Huruf', href: '#ways' },
      { label: 'Review 3 Zona & Reject', href: '#platform' },
      { label: 'Daftar Kata Kunci Blokir', href: '#features' },
    ],
  },
  {
    title: 'Analisis Channel',
    links: [
      { label: 'Asisten Analisis Spam', href: '#features' },
      { label: 'Akun Spammer Terbanyak', href: '#platform' },
      { label: 'Pola Jam Serangan Spam', href: '#platform' },
      { label: 'Perbandingan Antar Video', href: '#platform' },
    ],
  },
  {
    title: 'Keamanan & Privasi',
    links: [
      { label: 'Login Resmi YouTube', href: '#security' },
      { label: 'Tanpa Reject Otomatis', href: '#security' },
      { label: 'Pembersihan Data 30 Hari', href: '#security' },
    ],
  },
  {
    title: 'Bantuan',
    links: [
      { label: 'Pertanyaan Umum (FAQ)', href: '#faq' },
      { label: 'Kembali ke Atas', href: '#top' },
    ],
  },
];

export function FooterSection() {
  const { go } = React.useContext(LandingCtx);

  const onLink = (href: string) => (e: React.MouseEvent) => {
    if (href.startsWith('#')) {
      e.preventDefault();
      go(href.slice(1));
    }
  };

  return (
    <footer className="msp-footer">
      <div className="msp-wrap">
        <div className="msp-foot-top">
          <div className="msp-foot-brand">
            <a href="#top" className="msp-brand" onClick={onLink('#top')}>
              <Mark />
              <span>JudolGuard</span>
            </a>
            <p>
              Asisten cerdas moderasi komentar judi online untuk pemilik channel YouTube. AI memberi rekomendasi,
              manusia yang memutuskan.
            </p>
          </div>
          {FOOTER_COLUMNS.map((c) => (
            <nav key={c.title} className="msp-foot-col" aria-label={c.title}>
              <p>{c.title}</p>
              {c.links.map((l) => (
                <a key={l.label} href={l.href} onClick={onLink(l.href)}>
                  {l.label}
                </a>
              ))}
            </nav>
          ))}
        </div>
        <div className="msp-foot-bottom">
          <p>© 2026 JudolGuard · Moderasi Komentar YouTube Berbasis AI.</p>
          <p className="msp-status">
            <i />
            Siap melindungi kolom komentar channel Anda
          </p>
        </div>
      </div>
    </footer>
  );
}

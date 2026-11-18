import {
  AlertTriangle,
  Ban,
  Bot,
  CheckCircle2,
  Cpu,
  Database,
  KeyRound,
  ListChecks,
  RefreshCw,
  ScanSearch,
  ServerCrash,
  Tags,
  XCircle,
} from 'lucide-react';
import type { ReactNode } from 'react';

import StatusBadge from '../components/StatusBadge';
import { useHealth } from '../hooks/useHealth';

const steps = [
  { icon: ScanSearch, title: 'Scan', desc: 'Ambil komentar secara batch (100/halaman) saat tombol Scan ditekan.' },
  { icon: Cpu, title: 'Klasifikasi', desc: 'Seluruh komentar dinilai sekaligus dalam satu array oleh model SVM.' },
  { icon: ListChecks, title: 'Review 3 zona', desc: 'Judol, perlu review, dan bukan judol — koreksi label bila perlu.' },
  { icon: Ban, title: 'Reject', desc: 'Reject terpilih dengan multi-ID batch (hingga 50 ID per panggilan).' },
  { icon: Tags, title: 'Kata kunci', desc: 'LLM mengekstrak nama situs untuk Blocked words YouTube Studio.' },
  { icon: Bot, title: 'Chatbot', desc: 'Tanya akun atau pola spam, dijawab dari data di database.' },
];

function Card({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2 text-slate-700">
        {icon}
        <h2 className="text-sm font-semibold uppercase tracking-wide">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 py-2 last:border-0">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="text-right text-sm font-medium text-slate-800">{children}</dd>
    </div>
  );
}

function Flag({ on, onText = 'Terisi', offText = 'Belum diisi' }: { on: boolean; onText?: string; offText?: string }) {
  return <StatusBadge tone={on ? 'ok' : 'muted'}>{on ? onText : offText}</StatusBadge>;
}

export default function HomePage() {
  const { data, error, isLoading, isFetching, refetch } = useHealth();
  const connected = !!data && !error;

  return (
    <div className="space-y-8">
      {/* Hero */}
      <section className="rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-600 p-8 text-white shadow-lg">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Moderasi komentar judol, lebih cepat.</h1>
        <p className="mt-3 max-w-2xl text-indigo-100">
          JudolGuard mengklasifikasikan komentar YouTube ke tiga zona dengan model TF-IDF + SVM, lalu Anda
          yang memutuskan komentar mana yang di-reject. Tidak ada reject otomatis.
        </p>
      </section>

      {/* Status koneksi */}
      <div
        className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4 ${
          isLoading
            ? 'border-slate-200 bg-white'
            : connected
              ? 'border-emerald-200 bg-emerald-50'
              : 'border-rose-200 bg-rose-50'
        }`}
      >
        <div className="flex items-center gap-3">
          {isLoading ? (
            <RefreshCw className="h-6 w-6 animate-spin text-slate-400" />
          ) : connected ? (
            <CheckCircle2 className="h-6 w-6 text-emerald-600" />
          ) : (
            <ServerCrash className="h-6 w-6 text-rose-600" />
          )}
          <div>
            <p className="font-semibold">
              {isLoading ? 'Memeriksa backend…' : connected ? 'Backend terhubung' : 'Backend tidak terhubung'}
            </p>
            <p className="text-sm text-slate-600">
              {connected
                ? `${data.app} v${data.version} · lingkungan ${data.environment}`
                : error
                  ? error.message
                  : 'Menghubungi /api/health'}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          Periksa ulang
        </button>
      </div>

      {connected && (
        <div className="grid gap-6 md:grid-cols-2">
          <Card title="Model ML" icon={<Cpu className="h-4 w-4" />}>
            <dl>
              <Row label="Status model">
                {data.ml.model_loaded ? (
                  <StatusBadge tone="ok">
                    <CheckCircle2 className="h-3 w-3" /> Dimuat
                  </StatusBadge>
                ) : (
                  <StatusBadge tone="error">
                    <XCircle className="h-3 w-3" /> Gagal dimuat
                  </StatusBadge>
                )}
              </Row>
              <Row label="Versi model">{data.ml.model_version}</Row>
              <Row label="scikit-learn">
                {data.ml.sklearn_version}{' '}
                <StatusBadge tone={data.ml.sklearn_version_match ? 'ok' : 'warn'}>
                  {data.ml.sklearn_version_match ? 'cocok' : `harus ${data.ml.expected_sklearn_version}`}
                </StatusBadge>
              </Row>
              <Row label="Hash normalizer.py">
                <span className="mr-2 font-mono text-xs text-slate-500">
                  {data.ml.normalizer_hash?.slice(0, 12)}…
                </span>
                {data.ml.normalizer_match ? (
                  <StatusBadge tone="ok">cocok</StatusBadge>
                ) : (
                  <StatusBadge tone="warn">
                    <AlertTriangle className="h-3 w-3" /> tidak cocok
                  </StatusBadge>
                )}
              </Row>
              {data.ml.thresholds && (
                <Row label="Ambang zona">
                  <span className="font-mono text-xs">
                    t_low={data.ml.thresholds.t_low.toFixed(3)} · t_high={data.ml.thresholds.t_high.toFixed(3)}
                  </span>
                </Row>
              )}
              {data.ml.load_error && <Row label="Galat">{data.ml.load_error}</Row>}
            </dl>
          </Card>

          <Card title="Konfigurasi (.env)" icon={<KeyRound className="h-4 w-4" />}>
            <dl>
              <Row label="Database Supabase (session pooler)">
                <Flag on={data.database.configured} />
              </Row>
              <Row label="Google OAuth">
                <Flag on={data.integrations.google_oauth_configured} />
              </Row>
              <Row label="Gemini API (utama)">
                <Flag on={data.integrations.gemini_configured} />
              </Row>
              <Row label="Groq API (cadangan)">
                <Flag on={data.integrations.groq_configured} />
              </Row>
            </dl>
            <p className="mt-3 flex items-start gap-2 text-xs text-slate-500">
              <Database className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              Nilai yang belum diisi akan dipakai mulai Part 2 (OAuth), Part 3 (Supabase), dan Part 7–8 (LLM).
            </p>
          </Card>
        </div>
      )}

      {/* Alur kerja */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Alur kerja JudolGuard</h2>
        <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {steps.map(({ icon: Icon, title, desc }, i) => (
            <li key={title} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-50 text-xs font-bold text-indigo-700">
                  {i + 1}
                </span>
                <Icon className="h-4 w-4 text-indigo-600" />
                <h3 className="font-semibold">{title}</h3>
              </div>
              <p className="mt-2 text-sm text-slate-600">{desc}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

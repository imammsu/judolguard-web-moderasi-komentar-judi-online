/**
 * VideosPage — Halaman tujuan setelah login OAuth YouTube berhasil.
 *
 * Saat ini berfungsi sebagai konfirmasi login berhasil dan placeholder
 * untuk daftar video channel yang akan diimplementasikan pada Part 4.
 */

import { CheckCircle2, LogOut, ShieldCheck, Video, Youtube } from 'lucide-react';
import { Link } from 'react-router-dom';

import { useAuth } from '../hooks/useAuth';

/* ─────────────────────────── Sub-components ─────────────────────────── */

function TopNav({ channelTitle, thumbnailUrl, email, onLogout, loggingOut }: {
  channelTitle: string;
  thumbnailUrl: string;
  email: string;
  onLogout: () => void;
  loggingOut: boolean;
}) {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 text-slate-900 hover:opacity-80 transition-opacity">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <span className="text-lg font-bold tracking-tight">JudolGuard</span>
        </Link>

        {/* Channel identity + logout */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 rounded-lg bg-slate-50 border border-slate-200 px-3 py-1.5">
            {thumbnailUrl ? (
              <img
                src={thumbnailUrl}
                alt={channelTitle}
                width={28}
                height={28}
                className="rounded-full ring-1 ring-slate-200"
              />
            ) : (
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold">
                {channelTitle.charAt(0).toUpperCase()}
              </span>
            )}
            <div className="leading-tight">
              <p className="text-sm font-semibold text-slate-800">{channelTitle}</p>
              <p className="text-xs text-slate-500">{email}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onLogout}
            disabled={loggingOut}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <LogOut className="h-4 w-4" />
            {loggingOut ? 'Keluar…' : 'Keluar'}
          </button>
        </div>
      </div>
    </header>
  );
}

function SuccessBanner({ channelTitle }: { channelTitle: string }) {
  return (
    <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6 sm:p-8">
      <div className="flex items-start gap-4">
        <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-100">
          <CheckCircle2 className="h-6 w-6 text-emerald-600" />
        </span>
        <div>
          <div className="mb-1 inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Login Berhasil
          </div>
          <h1 className="mt-1 text-xl font-bold text-slate-900 sm:text-2xl">
            Selamat datang, {channelTitle}!
          </h1>
          <p className="mt-1 text-sm text-emerald-700">
            Akun YouTube Anda berhasil terhubung dengan izin moderasi komentar.
            JudolGuard kini dapat memindai dan mengelola komentar channel Anda.
          </p>
        </div>
      </div>
    </div>
  );
}

function StatusCard({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${accent ? 'border-indigo-200 bg-indigo-50' : 'border-slate-200 bg-white'}`}>
      <p className={`text-xs font-medium uppercase tracking-wide ${accent ? 'text-indigo-500' : 'text-slate-500'}`}>
        {label}
      </p>
      <p className={`mt-1 text-lg font-bold ${accent ? 'text-indigo-700' : 'text-slate-800'}`}>
        {value}
      </p>
    </div>
  );
}

function VideoPlaceholder() {
  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-slate-900">Daftar Video Channel</h2>
        <p className="mt-1 text-sm text-slate-500">
          Pilih video untuk mulai memindai komentar spam dan promosi judi online.
        </p>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatusCard label="Status Akun" value="Terhubung" accent />
        <StatusCard label="Kuota Scan" value="Siap Digunakan" />
        <StatusCard label="Video Dipindai" value="0 Video" />
      </div>

      {/* Placeholder card */}
      <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50/60 py-16 px-6 text-center">
        <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-100 text-indigo-600">
          <Video className="h-7 w-7" />
        </span>
        <div className="max-w-sm space-y-1">
          <p className="font-semibold text-slate-800">Daftar video segera hadir</p>
          <p className="text-sm text-slate-500">
            Daftar video channel Anda akan dimuat di sini pada tahap berikutnya —
            lengkap dengan tombol Scan untuk memindai komentar per video.
          </p>
        </div>
        <span className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-600">
          Akan hadir: Part 4 · YouTube Data API & Pemindaian Komentar
        </span>
      </div>
    </section>
  );
}

function AccessDenied({ onLogin }: { onLogin: () => void }) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="max-w-sm space-y-5 text-center">
        <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100">
          <ShieldCheck className="h-7 w-7 text-amber-600" />
        </span>
        <div>
          <h2 className="text-lg font-bold text-slate-900">Akses Dibatasi</h2>
          <p className="mt-2 text-sm text-slate-600">
            Silakan hubungkan channel YouTube Anda terlebih dahulu untuk mengakses
            fitur moderasi komentar JudolGuard.
          </p>
        </div>
        <button
          type="button"
          onClick={onLogin}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
        >
          <Youtube className="h-4 w-4" />
          Masuk dengan YouTube
        </button>
        <p className="text-xs text-slate-400">
          <Link to="/" className="underline underline-offset-2 hover:text-slate-600">
            Kembali ke beranda
          </Link>
        </p>
      </div>
    </div>
  );
}

/* ─────────────────────────── Main Page ─────────────────────────── */

export default function VideosPage() {
  const { user, loading, login, logout, loggingOut } = useAuth();

  // Sedang memuat status sesi — tampilkan spinner halus
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="text-center space-y-3">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100">
            <ShieldCheck className="h-6 w-6 animate-pulse text-indigo-600" />
          </span>
          <p className="text-sm font-medium text-slate-500">Memuat sesi…</p>
        </div>
      </div>
    );
  }

  // Belum login — tampilkan halaman akses ditolak
  if (!user) {
    return (
      <div className="min-h-screen bg-slate-50 px-4">
        <div className="mx-auto max-w-6xl py-8">
          <AccessDenied onLogin={() => login('/videos')} />
        </div>
      </div>
    );
  }

  // Sudah login — tampilkan halaman utama
  return (
    <div className="min-h-screen bg-slate-50">
      <TopNav
        channelTitle={user.channel_title}
        thumbnailUrl={user.thumbnail_url}
        email={user.email}
        onLogout={logout}
        loggingOut={loggingOut}
      />
      <main className="mx-auto max-w-6xl space-y-8 px-4 py-8 sm:px-6">
        <SuccessBanner channelTitle={user.channel_title} />
        <VideoPlaceholder />
      </main>
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        JudolGuard · AI memberi rekomendasi, manusia memutuskan.
      </footer>
    </div>
  );
}

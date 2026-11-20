import {
  AlertCircle,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  LogOut,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
  Video,
  Youtube,
} from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { ApiError } from '../api/client';
import { useAuth } from '../hooks/useAuth';
import { useVideos } from '../hooks/useVideos';
import type { VideoItem } from '../types/api';

function TopNav({
  channelTitle,
  thumbnailUrl,
  email,
  onLogout,
  loggingOut,
}: {
  channelTitle: string;
  thumbnailUrl: string;
  email: string;
  onLogout: () => void;
  loggingOut: boolean;
}) {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2 text-slate-900 transition-opacity hover:opacity-80">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <span className="text-lg font-bold tracking-tight">JudolGuard</span>
        </Link>

        <div className="flex items-center gap-3">
          <div className="hidden items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 sm:flex">
            {thumbnailUrl ? (
              <img
                src={thumbnailUrl}
                alt={channelTitle}
                width={28}
                height={28}
                className="rounded-full ring-1 ring-slate-200"
              />
            ) : (
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">
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
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <LogOut className="h-4 w-4" />
            {loggingOut ? 'Keluar…' : 'Keluar'}
          </button>
        </div>
      </div>
    </header>
  );
}

function formatDate(value: string | null) {
  if (!value) return 'Tanggal tidak tersedia';
  return new Intl.DateTimeFormat('id-ID', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value));
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('id-ID').format(value);
}

function scanStatusLabel(status: VideoItem['scan_status']) {
  if (status === 'not_scanned') return 'Belum discan';
  if (status === 'queued') return 'Scan dalam antrean';
  if (status === 'running') return 'Scan sedang berjalan';
  if (status === 'failed') return 'Scan terakhir gagal';
  return 'Scan selesai';
}

function VideoCard({ video }: { video: VideoItem }) {
  return (
    <Link
      to={`/videos/${encodeURIComponent(video.video_id)}`}
      className="block overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="aspect-video overflow-hidden bg-slate-100">
        {video.thumbnail_url ? (
          <img
            src={video.thumbnail_url}
            alt=""
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-slate-400">
            <Video className="h-10 w-10" />
          </div>
        )}
      </div>
      <div className="space-y-4 p-4">
        <h3 className="line-clamp-2 min-h-12 font-semibold leading-6 text-slate-900">{video.title}</h3>
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-500">
          <span className="inline-flex items-center gap-1.5">
            <CalendarDays className="h-3.5 w-3.5" />
            {formatDate(video.published_at)}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <MessageSquare className="h-3.5 w-3.5" />
            {formatNumber(video.comment_count)} komentar di YouTube
          </span>
        </div>
        <div className="space-y-1 rounded-lg bg-indigo-50 px-3 py-2 text-xs font-medium text-indigo-700">
          <p>{scanStatusLabel(video.scan_status)}</p>
          {video.scan_status === 'done' && (
            <p className="font-normal text-indigo-600">
              {formatNumber(video.stored_comment_count)} komentar tersedia untuk moderasi
            </p>
          )}
          {video.scan_status === 'not_scanned' && (
            <p className="font-normal text-indigo-600">Pilih video untuk menyiapkan pemindaian komentar</p>
          )}
        </div>
      </div>
    </Link>
  );
}

function VideoSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="aspect-video animate-pulse bg-slate-200" />
      <div className="space-y-3 p-4">
        <div className="h-5 animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-slate-100" />
        <div className="h-9 animate-pulse rounded bg-slate-100" />
      </div>
    </div>
  );
}

function VideoLibrary() {
  const [page, setPage] = useState(1);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const { data, error, isLoading, isFetching, refetch, refresh: refreshVideos } = useVideos(page, 12);

  const refreshList = async () => {
    setRefreshError(null);
    setIsRefreshing(true);
    try {
      await refreshVideos();
    } catch (error) {
      setRefreshError(error instanceof Error ? error.message : 'Daftar video gagal diperbarui.');
    } finally {
      setIsRefreshing(false);
    }
  };

  if (isLoading) {
    return (
      <section className="space-y-6">
        <div className="h-8 w-56 animate-pulse rounded bg-slate-200" />
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }, (_, index) => <VideoSkeleton key={index} />)}
        </div>
      </section>
    );
  }

  if (error) {
    const message = error instanceof ApiError ? error.message : 'Daftar video belum dapat dimuat.';
    return (
      <section className="rounded-2xl border border-rose-200 bg-rose-50 p-6">
        <div className="flex items-start gap-3">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" />
          <div>
            <h2 className="font-semibold text-rose-900">Gagal memuat daftar video</h2>
            <p className="mt-1 text-sm text-rose-700">{message}</p>
            <button
              type="button"
              onClick={() => refetch()}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-rose-600 px-3 py-2 text-sm font-semibold text-white hover:bg-rose-700"
            >
              <RefreshCw className="h-4 w-4" />
              Coba lagi
            </button>
          </div>
        </div>
      </section>
    );
  }

  const items = data?.items ?? [];
  const hasPages = (data?.total_pages ?? 0) > 1;

  return (
    <section className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium text-indigo-600">Channel YouTube terhubung</p>
          <h2 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">Daftar video</h2>
          <p className="mt-1 text-sm text-slate-500">
            Video tersimpan sebagai cache. Komentar belum diambil pada tahap ini.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refreshList()}
          disabled={isFetching || isRefreshing}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${isFetching || isRefreshing ? 'animate-spin' : ''}`} />
          {isFetching || isRefreshing ? 'Memperbarui…' : 'Perbarui daftar'}
        </button>
      </div>

      {refreshError && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {refreshError}
        </div>
      )}
      {data?.sync_mode === 'incremental' && (
        <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-800">
          {data.new_videos > 0
            ? `${formatNumber(data.new_videos)} video baru ditemukan dan disimpan.`
            : 'Tidak ada video baru.'}{' '}
          {formatNumber(data.updated_videos)} metadata video diperbarui. Estimasi penggunaan API:{' '}
          {formatNumber(data.estimated_quota)} request.
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Total video</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{formatNumber(data?.total ?? 0)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Status sinkronisasi</p>
          <p className="mt-1 inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-700">
            <CheckCircle2 className="h-4 w-4" />
            Tersimpan di database
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Tahap berikutnya</p>
          <p className="mt-1 text-sm font-semibold text-indigo-700">Scan komentar per video</p>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 px-6 py-16 text-center">
          <Video className="mx-auto h-10 w-10 text-slate-400" />
          <h3 className="mt-4 font-semibold text-slate-800">Belum ada video</h3>
          <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
            Channel ini belum memiliki video publik yang dapat ditampilkan.
          </p>
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((video) => <VideoCard key={video.video_id} video={video} />)}
        </div>
      )}

      {hasPages && (
        <div className="flex items-center justify-between border-t border-slate-200 pt-5">
          <p className="text-sm text-slate-500">
            Halaman {data?.page} dari {data?.total_pages}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={page === 1 || isFetching}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
              Sebelumnya
            </button>
            <button
              type="button"
              onClick={() => setPage((current) => current + 1)}
              disabled={page >= (data?.total_pages ?? 0) || isFetching}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Berikutnya
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
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
          <h2 className="text-lg font-bold text-slate-900">Akses dibatasi</h2>
          <p className="mt-2 text-sm text-slate-600">
            Hubungkan channel YouTube terlebih dahulu untuk melihat daftar video.
          </p>
        </div>
        <button
          type="button"
          onClick={onLogin}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
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

export default function VideosPage() {
  const { user, loading, login, logout, loggingOut } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="space-y-3 text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100">
            <ShieldCheck className="h-6 w-6 animate-pulse text-indigo-600" />
          </span>
          <p className="text-sm font-medium text-slate-500">Memuat sesi…</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-slate-50 px-4">
        <div className="mx-auto max-w-6xl py-8">
          <AccessDenied onLogin={() => login('/videos')} />
        </div>
      </div>
    );
  }

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
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
            <div>
              <p className="font-semibold text-emerald-900">Channel berhasil terhubung</p>
              <p className="mt-1 text-sm text-emerald-700">
                Daftar video diambil dari YouTube dan disimpan ke database JudolGuard.
              </p>
            </div>
          </div>
        </div>
        <VideoLibrary />
      </main>
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        JudolGuard · AI memberi rekomendasi, manusia memutuskan.
      </footer>
    </div>
  );
}

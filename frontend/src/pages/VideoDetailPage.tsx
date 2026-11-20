import {
  AlertCircle,
  ArrowLeft,
  Ban,
  Bot,
  CheckCircle2,
  Filter,
  Heart,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  X,
  Youtube,
} from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ApiError } from '../api/client';
import { useAuth } from '../hooks/useAuth';
import { type RejectTarget, useModeration } from '../hooks/useModeration';
import { useScanJob } from '../hooks/useScanJob';
import { useVideoComments } from '../hooks/useVideoComments';
import { useVideoDetail } from '../hooks/useVideoDetail';

function formatDate(value: string | null) {
  if (!value) return 'Tanggal tidak tersedia';
  return new Intl.DateTimeFormat('id-ID', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('id-ID').format(value);
}

function ZoneBadge({ zone }: { zone: 'judol' | 'review' | 'bukan' | null }) {
  const style = {
    judol: 'bg-rose-100 text-rose-700',
    review: 'bg-amber-100 text-amber-700',
    bukan: 'bg-emerald-100 text-emerald-700',
  }[zone || 'review'];
  const label = { judol: 'Judol', review: 'Perlu review', bukan: 'Bukan judol' }[zone || 'review'];
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${style}`}>{label}</span>;
}

function ScanProgress({
  status,
  progress,
  processed,
  total,
  error,
}: {
  status: string;
  progress: number;
  processed: number;
  total: number;
  error: string | null;
}) {
  if (!status) return null;
  const failed = status === 'failed';
  const done = status === 'done';
  return (
    <div className={`rounded-xl border p-4 ${failed ? 'border-rose-200 bg-rose-50' : done ? 'border-emerald-200 bg-emerald-50' : 'border-indigo-200 bg-indigo-50'}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {failed ? (
            <AlertCircle className="h-5 w-5 text-rose-600" />
          ) : done ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          ) : (
            <LoaderCircle className="h-5 w-5 animate-spin text-indigo-600" />
          )}
          <p className="text-sm font-semibold">
            {failed ? 'Scan gagal' : done ? 'Scan selesai' : status === 'queued' ? 'Menunggu scan…' : 'Scan & klasifikasi berjalan…'}
          </p>
        </div>
        <span className="text-sm font-bold">{progress}%</span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/80">
        <div
          className={`h-full rounded-full transition-all ${failed ? 'bg-rose-500' : done ? 'bg-emerald-500' : 'bg-indigo-600'}`}
          style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-slate-600">
        {total > 0 ? `${formatNumber(processed)} dari ${formatNumber(total)} komentar diproses.` : 'Mengambil komentar terbaru dari YouTube.'}
      </p>
      {error && <p className="mt-2 text-sm text-rose-700">{error}</p>}
    </div>
  );
}

function CommentTable({
  videoId,
  onRequestReject,
  selectionResetToken,
}: {
  videoId: string;
  onRequestReject: (target: RejectTarget) => void;
  selectionResetToken: number;
}) {
  const [zone, setZone] = useState('all');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [sort, setSort] = useState('score_desc');
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const filters = { zone, search, sort, page, pageSize: 50 };
  const { data, error, isLoading, isFetching, refetch } = useVideoComments(videoId, filters);
  const selectableIds = (data?.items ?? [])
    .filter((comment) => comment.moderation_status !== 'rejected')
    .map((comment) => comment.comment_id);
  const allPageSelected = selectableIds.length > 0 && selectableIds.every((id) => selectedIds.has(id));

  useEffect(() => {
    setSelectedIds(new Set());
  }, [selectionResetToken]);

  const toggleSelected = (commentId: string) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(commentId)) next.delete(commentId);
      else next.add(commentId);
      return next;
    });
  };

  const toggleAllPage = () => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (allPageSelected) selectableIds.forEach((id) => next.delete(id));
      else selectableIds.forEach((id) => next.add(id));
      return next;
    });
  };

  const applySearch = () => {
    setPage(1);
    setSearch(searchInput);
  };

  if (error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
        <p className="font-semibold">Komentar belum dapat dimuat.</p>
        <p className="mt-1">{error instanceof ApiError ? error.message : 'Terjadi kesalahan.'}</p>
        <button type="button" onClick={() => refetch()} className="mt-3 inline-flex items-center gap-2 rounded-lg bg-rose-600 px-3 py-2 font-semibold text-white">
          <RefreshCw className="h-4 w-4" /> Coba lagi
        </button>
      </div>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 lg:flex-row">
        <div className="flex flex-1 gap-2">
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && applySearch()}
            placeholder="Cari isi komentar…"
            className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
          />
          <button type="button" onClick={applySearch} className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-900">
            Cari
          </button>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <Filter className="h-4 w-4" />
          <select value={zone} onChange={(event) => { setPage(1); setZone(event.target.value); }} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
            <option value="all">Semua zona</option>
            <option value="judol">Judol</option>
            <option value="review">Perlu review</option>
            <option value="bukan">Bukan judol</option>
          </select>
        </label>
        <select value={sort} onChange={(event) => { setPage(1); setSort(event.target.value); }} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
          <option value="score_desc">Skor tertinggi</option>
          <option value="score_asc">Skor terendah</option>
          <option value="newest">Terbaru</option>
          <option value="oldest">Terlama</option>
        </select>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3">
        <label className="inline-flex items-center gap-2 text-sm font-medium text-indigo-900">
          <input
            type="checkbox"
            checked={allPageSelected}
            onChange={toggleAllPage}
            disabled={!selectableIds.length}
            className="h-4 w-4 rounded border-indigo-300 text-indigo-600"
          />
          Pilih semua di halaman
        </label>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!selectedIds.size}
            onClick={() => onRequestReject({ comment_ids: Array.from(selectedIds) })}
            className="inline-flex items-center gap-2 rounded-lg bg-rose-600 px-3 py-2 text-xs font-semibold text-white hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Ban className="h-3.5 w-3.5" />
            Reject terpilih ({selectedIds.size})
          </button>
          <button
            type="button"
            onClick={() => onRequestReject({ video_id: videoId, all_judol: true })}
            className="inline-flex items-center gap-2 rounded-lg border border-rose-300 bg-white px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50"
          >
            <Ban className="h-3.5 w-3.5" />
            Reject semua judol
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        {isLoading ? (
          <div className="flex items-center justify-center gap-2 px-5 py-16 text-sm text-slate-500">
            <LoaderCircle className="h-5 w-5 animate-spin" /> Memuat komentar…
          </div>
        ) : data?.items.length ? (
          <div className="divide-y divide-slate-100">
            {data.items.map((comment) => (
              <article key={comment.comment_id} className="space-y-3 p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(comment.comment_id)}
                      onChange={() => toggleSelected(comment.comment_id)}
                      disabled={comment.moderation_status === 'rejected'}
                      className="mt-1 h-4 w-4 rounded border-slate-300 text-indigo-600"
                      aria-label={`Pilih komentar dari ${comment.author_name || 'akun YouTube'}`}
                    />
                    <div>
                      <p className="text-sm font-semibold text-slate-800">{comment.author_name || 'Akun YouTube'}</p>
                      <p className="mt-0.5 text-xs text-slate-400">{formatDate(comment.published_at)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <ZoneBadge zone={comment.zone} />
                    {comment.score !== null && (
                      <span className="font-mono text-xs text-slate-500">skor {(comment.score * 100).toFixed(1)}%</span>
                    )}
                  </div>
                </div>
                <p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-700">{comment.text_original}</p>
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                  <span className="inline-flex items-center gap-1"><Heart className="h-3.5 w-3.5" /> {formatNumber(comment.like_count)} like</span>
                  {comment.rule_hit && <span className="rounded bg-amber-50 px-2 py-1 font-medium text-amber-700">Terkena aturan iklan</span>}
                  <span>Status: {comment.moderation_status === 'rejected' ? 'Sudah direject' : 'Belum direject'}</span>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="px-5 py-16 text-center text-sm text-slate-500">
            Belum ada komentar yang sesuai filter. Jalankan Scan & Klasifikasi terlebih dahulu.
          </div>
        )}
      </div>

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between text-sm text-slate-500">
          <span>{formatNumber(data.total)} komentar</span>
          <div className="flex gap-2">
            <button type="button" disabled={page <= 1 || isFetching} onClick={() => setPage((current) => current - 1)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 disabled:opacity-40">Sebelumnya</button>
            <span className="px-2 py-2">Halaman {data.page} / {data.total_pages}</span>
            <button type="button" disabled={page >= data.total_pages || isFetching} onClick={() => setPage((current) => current + 1)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 disabled:opacity-40">Berikutnya</button>
          </div>
        </div>
      )}
    </section>
  );
}

function RejectDialog({
  preview,
  pending,
  error,
  onClose,
  onConfirm,
}: {
  preview: {
    estimate: {
      comment_count: number;
      batch_count: number;
      ids_per_batch: number;
      estimated_quota_units: number;
      remaining_quota_units: number;
      sufficient: boolean;
    };
    quota: {
      used_units: number;
      daily_limit: number;
      remaining_units: number;
    };
  };
  pending: boolean;
  error: Error | null;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const { estimate, quota } = preview;
  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-950/40 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-rose-600">Konfirmasi moderasi</p>
            <h2 className="mt-1 text-xl font-bold text-slate-900">Reject komentar?</h2>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Tutup dialog">
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Komentar akan disembunyikan dari publik YouTube. Aksi ini tidak dapat dibatalkan dari JudolGuard.
        </p>
        <dl className="mt-5 divide-y divide-slate-100 rounded-xl border border-slate-200 px-4">
          <div className="flex justify-between gap-4 py-3 text-sm">
            <dt className="text-slate-500">Komentar dipilih</dt>
            <dd className="font-semibold text-slate-900">{formatNumber(estimate.comment_count)}</dd>
          </div>
          <div className="flex justify-between gap-4 py-3 text-sm">
            <dt className="text-slate-500">Jumlah batch</dt>
            <dd className="font-semibold text-slate-900">{formatNumber(estimate.batch_count)} × maksimal {estimate.ids_per_batch} ID</dd>
          </div>
          <div className="flex justify-between gap-4 py-3 text-sm">
            <dt className="text-slate-500">Estimasi kuota</dt>
            <dd className="font-semibold text-rose-700">±{formatNumber(estimate.estimated_quota_units)} unit</dd>
          </div>
          <div className="flex justify-between gap-4 py-3 text-sm">
            <dt className="text-slate-500">Kuota tersisa</dt>
            <dd className="font-semibold text-slate-900">{formatNumber(quota.remaining_units)} unit</dd>
          </div>
        </dl>
        {!estimate.sufficient && (
          <p className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700">
            Kuota harian tidak mencukupi untuk aksi ini.
          </p>
        )}
        {error && <p className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error.message}</p>}
        <div className="mt-6 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
            Batal
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={!estimate.sufficient || pending}
            className="inline-flex items-center gap-2 rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {pending && <LoaderCircle className="h-4 w-4 animate-spin" />}
            {pending ? 'Memproses…' : 'Konfirmasi Reject'}
          </button>
        </div>
      </div>
    </div>
  );
}

function AccessDenied({ onLogin }: { onLogin: () => void }) {
  return (
    <div className="flex min-h-[70vh] items-center justify-center px-4">
      <div className="max-w-sm text-center">
        <ShieldCheck className="mx-auto h-12 w-12 text-amber-600" />
        <h1 className="mt-4 text-xl font-bold text-slate-900">Login diperlukan</h1>
        <p className="mt-2 text-sm text-slate-600">Hubungkan channel YouTube untuk memindai komentar.</p>
        <button type="button" onClick={onLogin} className="mt-5 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700">
          <Youtube className="h-4 w-4" /> Masuk dengan YouTube
        </button>
      </div>
    </div>
  );
}

export default function VideoDetailPage() {
  const { videoId = '' } = useParams();
  const { user, loading: authLoading, login, logout, loggingOut } = useAuth();
  const queryClient = useQueryClient();
  const { data: video, isLoading: videoLoading, error: videoError } = useVideoDetail(videoId, Boolean(user));
  const { mutate: startScan, isPending: scanStarting, job, resetJob } = useScanJob(videoId);
  const { preview, reject } = useModeration(videoId);
  const [rejectTarget, setRejectTarget] = useState<RejectTarget | null>(null);
  const [moderationResult, setModerationResult] = useState<string | null>(null);
  const [selectionResetToken, setSelectionResetToken] = useState(0);

  useEffect(() => {
    if (job?.status === 'done') {
      void queryClient.invalidateQueries({ queryKey: ['video-comments', videoId] });
      void queryClient.invalidateQueries({ queryKey: ['video', videoId] });
    }
  }, [job?.status, queryClient, videoId]);

  if (authLoading || videoLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-50 text-sm text-slate-500">Memuat halaman video…</div>;
  }
  if (!user) return <AccessDenied onLogin={() => login(`/videos/${videoId}`)} />;
  if (videoError || !video) {
    return <div className="mx-auto max-w-3xl px-4 py-16 text-center text-sm text-rose-700">{videoError instanceof Error ? videoError.message : 'Video tidak ditemukan.'}</div>;
  }

  const running = job && (job.status === 'queued' || job.status === 'running');
  const completed = job?.status === 'done';
  const requestReject = (target: RejectTarget) => {
    setRejectTarget(target);
    setModerationResult(null);
    preview.reset();
    reject.reset();
    preview.mutate(target);
  };
  const closeRejectDialog = () => {
    setRejectTarget(null);
    preview.reset();
    reject.reset();
  };
  const confirmReject = () => {
    if (!rejectTarget) return;
    reject.mutate(rejectTarget, {
      onSuccess: (summary) => {
        setModerationResult(
          summary.failed > 0
            ? `${formatNumber(summary.succeeded)} komentar berhasil direject, ${formatNumber(summary.failed)} gagal.`
            : `${formatNumber(summary.succeeded)} komentar berhasil direject.`,
        );
        setSelectionResetToken((current) => current + 1);
        closeRejectDialog();
      },
    });
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link to="/videos" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-indigo-700"><ArrowLeft className="h-4 w-4" /> Daftar video</Link>
          <button type="button" onClick={logout} disabled={loggingOut} className="text-sm font-medium text-slate-500 hover:text-slate-900">{loggingOut ? 'Keluar…' : 'Keluar'}</button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="grid gap-0 md:grid-cols-[280px_1fr]">
            <div className="aspect-video bg-slate-100 md:aspect-auto">
              {video.thumbnail_url && <img src={video.thumbnail_url} alt="" className="h-full w-full object-cover" />}
            </div>
            <div className="space-y-4 p-6">
              <p className="text-sm font-medium text-indigo-600">Detail video</p>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">{video.title}</h1>
              <p className="text-sm text-slate-500">{formatNumber(video.comment_count)} komentar · Dipublikasikan {formatDate(video.published_at)}</p>
              <button
                type="button"
                disabled={Boolean(running) || scanStarting}
                onClick={() => { resetJob(); startScan(); }}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {running || scanStarting ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
                {running || scanStarting ? 'Scan berjalan…' : completed ? 'Scan ulang' : 'Scan & Klasifikasi'}
              </button>
              <p className="text-xs text-slate-400">Komentar hanya diambil saat tombol scan ditekan.</p>
            </div>
          </div>
        </section>

        {job && <ScanProgress status={job.status} progress={job.progress} processed={job.processed} total={job.total} error={job.error} />}

        {moderationResult && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
            {moderationResult}
          </div>
        )}
        <CommentTable
          videoId={videoId}
          onRequestReject={requestReject}
          selectionResetToken={selectionResetToken}
        />
      </main>
      {rejectTarget && preview.data && (
        <RejectDialog
          preview={preview.data}
          pending={reject.isPending}
          error={reject.error instanceof Error ? reject.error : null}
          onClose={closeRejectDialog}
          onConfirm={confirmReject}
        />
      )}
      {rejectTarget && preview.isPending && !preview.data && (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-950/40 px-4">
          <div className="flex items-center gap-3 rounded-xl bg-white px-5 py-4 text-sm font-medium text-slate-700 shadow-xl">
            <LoaderCircle className="h-5 w-5 animate-spin text-indigo-600" />
            Menghitung estimasi kuota…
          </div>
        </div>
      )}
      {rejectTarget && preview.error && !preview.isPending && (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-950/40 px-4">
          <div className="max-w-md rounded-xl bg-white p-5 shadow-xl">
            <p className="font-semibold text-rose-800">Tidak dapat menyiapkan reject</p>
            <p className="mt-2 text-sm text-slate-600">{preview.error instanceof Error ? preview.error.message : 'Terjadi kesalahan.'}</p>
            <button type="button" onClick={closeRejectDialog} className="mt-4 rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white">Tutup</button>
          </div>
        </div>
      )}
    </div>
  );
}

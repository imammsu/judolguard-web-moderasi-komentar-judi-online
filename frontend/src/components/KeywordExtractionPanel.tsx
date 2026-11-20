import {
  AlertCircle,
  Check,
  CheckCircle2,
  Copy,
  Filter,
  KeyRound,
  LoaderCircle,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { ApiError } from '../api/client';
import { useKeywordExtraction } from '../hooks/useKeywordExtraction';
import { useVideoKeywords } from '../hooks/useVideoKeywords';
import type { VideoItem } from '../types/api';

function formatNumber(value: number) {
  return new Intl.NumberFormat('id-ID').format(value);
}

function typeLabel(type: 'situs' | 'kata_kunci') {
  return type === 'situs' ? 'Situs' : 'Kata kunci';
}

function typeStyle(type: 'situs' | 'kata_kunci') {
  return type === 'situs'
    ? 'bg-rose-100 text-rose-700'
    : 'bg-indigo-100 text-indigo-700';
}

async function copyToClipboard(value: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = value;
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand('copy');
  textarea.remove();
  if (!copied) throw new Error('Clipboard tidak tersedia.');
}

function ExtractionProgress({
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
            {failed ? 'Ekstraksi gagal' : done ? 'Ekstraksi selesai' : status === 'queued' ? 'Menunggu ekstraksi…' : 'Ekstraksi keyword berjalan…'}
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
        {total > 0 ? `${formatNumber(processed)} dari ${formatNumber(total)} batch diproses.` : 'Menyiapkan komentar judol untuk dianalisis.'}
      </p>
      {error && <p className="mt-2 text-sm text-rose-700">{error}</p>}
    </div>
  );
}

export function KeywordExtractionPanel({
  videoId,
  scanStatus,
  scanRunning,
}: {
  videoId: string;
  scanStatus: VideoItem['scan_status'];
  scanRunning: boolean;
}) {
  const { data, isLoading, isFetching, error, refetch } = useVideoKeywords(videoId);
  const {
    start,
    startPending,
    startError,
    job,
  } = useKeywordExtraction(videoId);
  const [filter, setFilter] = useState<'all' | 'situs' | 'kata_kunci'>('all');
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    if (!copied) return undefined;
    const timer = window.setTimeout(() => setCopied(null), 1800);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const filteredItems = useMemo(
    () => filter === 'all' ? items : items.filter((item) => item.type === filter),
    [filter, items],
  );
  const extractionRunning = Boolean(job && (job.status === 'queued' || job.status === 'running'));
  const canExtract = scanStatus === 'done' && !scanRunning && !startPending && !extractionRunning;
  const errorMessage = startError instanceof ApiError
    ? startError.message
    : startError instanceof Error
      ? startError.message
      : error instanceof ApiError
        ? error.message
        : error instanceof Error
          ? error.message
          : null;
  const allKeywords = items.map((item) => item.keyword).join(', ');

  const copyValue = async (value: string, key: string) => {
    try {
      await copyToClipboard(value);
      setCopied(key);
    } catch {
      setCopied(null);
    }
  };

  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-100 text-violet-700">
            <KeyRound className="h-5 w-5" />
          </span>
          <div>
            <p className="text-sm font-medium text-violet-600">Analisis NER</p>
            <h2 className="mt-1 text-lg font-bold text-slate-900">Ekstraksi keyword judol</h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
              Gemini digunakan sebagai model utama dan Groq sebagai fallback. Hanya komentar zona judol yang dianalisis.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => start()}
          disabled={!canExtract}
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {startPending || extractionRunning ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {startPending || extractionRunning ? 'Menyiapkan…' : data?.total ? 'Ekstrak ulang' : 'Ekstrak Keyword'}
        </button>
      </div>

      {scanStatus !== 'done' && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {scanRunning || scanStatus === 'running' || scanStatus === 'queued'
            ? 'Tunggu sampai Scan & Klasifikasi selesai.'
            : 'Jalankan Scan & Klasifikasi terlebih dahulu.'}
        </div>
      )}

      {job && <ExtractionProgress status={job.status} progress={job.progress} processed={job.processed} total={job.total} error={job.error} />}
      {errorMessage && !job?.error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {errorMessage}
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center gap-2 rounded-xl border border-slate-100 px-4 py-10 text-sm text-slate-500">
          <LoaderCircle className="h-5 w-5 animate-spin" /> Memuat hasil keyword…
        </div>
      ) : data?.total ? (
        <>
          <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Filter className="h-4 w-4" />
              <select
                value={filter}
                onChange={(event) => setFilter(event.target.value as typeof filter)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700"
                aria-label="Filter tipe keyword"
              >
                <option value="all">Semua tipe</option>
                <option value="situs">Situs</option>
                <option value="kata_kunci">Kata kunci</option>
              </select>
              <span className="text-xs text-slate-400">{formatNumber(filteredItems.length)} ditampilkan</span>
            </div>
            <button
              type="button"
              onClick={() => void copyValue(allKeywords, 'all')}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              {copied === 'all' ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
              {copied === 'all' ? 'Tersalin' : 'Salin semua'}
            </button>
          </div>

          {filteredItems.length ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {filteredItems.map((item) => (
                <article key={item.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <p className="break-words font-semibold text-slate-900">{item.keyword}</p>
                    <button
                      type="button"
                      onClick={() => void copyValue(item.keyword, String(item.id))}
                      className="shrink-0 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                      aria-label={`Salin keyword ${item.keyword}`}
                    >
                      {copied === String(item.id) ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
                    </button>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-2 text-xs">
                    <span className={`rounded-full px-2.5 py-1 font-semibold ${typeStyle(item.type)}`}>{typeLabel(item.type)}</span>
                    <span className="text-slate-500">{formatNumber(item.frequency)} komentar</span>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-slate-200 px-4 py-8 text-center text-sm text-slate-500">
              Tidak ada keyword untuk filter ini.
            </div>
          )}
        </>
      ) : (
        <div className="rounded-xl border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">
          Belum ada hasil ekstraksi keyword.
        </div>
      )}

      {data?.total ? (
        <div className="flex items-center justify-between gap-3 text-xs text-slate-400">
          <span>{formatNumber(data.total)} keyword tersimpan</span>
          <button type="button" onClick={() => void refetch()} disabled={isFetching} className="inline-flex items-center gap-1 hover:text-slate-700 disabled:opacity-50">
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} /> Perbarui
          </button>
        </div>
      ) : null}
    </section>
  );
}

import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  Link2,
  LoaderCircle,
  Send,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { ApiError } from '../api/client';
import { useTelegramPairing } from '../hooks/useTelegramPairing';

export default function TelegramConnectionCard() {
  const [waitingForPairing, setWaitingForPairing] = useState(false);
  const [pairingUrl, setPairingUrl] = useState<string | null>(null);
  const {
    status,
    statusLoading,
    statusError,
    createPairing,
    creatingPairing,
    pairingError,
  } = useTelegramPairing(waitingForPairing);

  useEffect(() => {
    if (status?.connected) {
      setWaitingForPairing(false);
      setPairingUrl(null);
    }
  }, [status?.connected]);

  const connectTelegram = async () => {
    let popup: Window | null = null;
    try {
      // Membuka tab saat masih berada dalam event klik agar tidak diblokir browser.
      popup = window.open('about:blank', '_blank');
      const pairing = await createPairing();
      setPairingUrl(pairing.pairing_url);
      setWaitingForPairing(true);
      if (popup) {
        popup.location.href = pairing.pairing_url;
        popup.opener = null;
      }
    } catch {
      popup?.close();
    }
  };

  const error = statusError || pairingError;
  const errorMessage =
    error instanceof ApiError
      ? error.message
      : 'Status Telegram tidak dapat dimuat. Coba lagi nanti.';

  if (statusLoading) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex animate-pulse items-center gap-3">
          <div className="h-11 w-11 rounded-xl bg-slate-200" />
          <div className="space-y-2">
            <div className="h-4 w-44 rounded bg-slate-200" />
            <div className="h-3 w-64 rounded bg-slate-100" />
          </div>
        </div>
      </section>
    );
  }

  if (status?.connected) {
    return (
      <section className="rounded-2xl border border-sky-200 bg-gradient-to-br from-sky-50 to-white p-5 shadow-sm">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-sky-100 text-sky-600">
            <Send className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-semibold text-slate-900">Telegram sudah terhubung</p>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-1 text-[11px] font-semibold text-emerald-700">
                <CheckCircle2 className="h-3 w-3" />
                Aktif
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-600">
              Notifikasi Sentinel akan dikirim ke {status.chat_id_masked}.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 via-white to-sky-50 p-5 shadow-sm">
      <div className="flex items-start gap-3">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-100 text-indigo-600">
          <Link2 className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-slate-900">Hubungkan Telegram</p>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Dapatkan notifikasi komentar judol baru tanpa harus membuka web.
          </p>
          <button
            type="button"
            onClick={() => void connectTelegram()}
            disabled={creatingPairing || waitingForPairing}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-wait disabled:opacity-60"
          >
            {creatingPairing ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {creatingPairing ? 'Menyiapkan tautan…' : 'Hubungkan Telegram'}
          </button>
        </div>
      </div>

      {waitingForPairing && (
        <div className="mt-4 rounded-xl border border-sky-200 bg-sky-50 px-3 py-3 text-sm text-sky-800">
          <p className="font-semibold">Menunggu konfirmasi Telegram</p>
          <p className="mt-1">
            Tekan tombol <strong>Start</strong> di bot Telegram. Status akan diperbarui
            otomatis.
          </p>
          {pairingUrl && (
            <a
              href={pairingUrl}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-flex items-center gap-1 font-semibold text-sky-700 hover:text-sky-900"
            >
              Buka ulang Telegram
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      )}

      {error && (
        <div className="mt-4 flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}
    </section>
  );
}

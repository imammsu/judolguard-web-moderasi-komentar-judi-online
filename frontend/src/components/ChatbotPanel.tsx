import { Bot, MessageCircle, Send, Sparkles, UserRound, X } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';

import { ApiError } from '../api/client';
import { useChatbot } from '../hooks/useChatbot';
import type { ChatMessage } from '../types/api';

const SUGGESTIONS = [
  'Akun mana yang paling sering spam?',
  'Berapa jumlah komentar judol?',
  'Keyword apa yang paling sering muncul?',
  'Jam berapa komentar judol paling banyak?',
];

export default function ChatbotPanel({ videoId }: { videoId?: string }) {
  const { ask, isPending, error, reset } = useChatbot(videoId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState('');
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  const sendQuestion = async (value: string) => {
    if (!value || isPending) return;
    const history = messages;
    const userMessage: ChatMessage = { role: 'user', content: value };
    setQuestion('');
    setMessages((current) => [...current, userMessage]);
    reset();

    try {
      const response = await ask({ question: value, history });
      setMessages((current) => [
        ...current,
        { role: 'assistant', content: response.answer },
      ]);
    } catch {
      // Pesan error ditampilkan dari mutation error di dalam drawer.
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void sendQuestion(question.trim());
  };

  return (
    <>
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-expanded={open}
          aria-controls="chatbot-drawer"
          className="inline-flex items-center gap-2 rounded-xl border border-indigo-200 bg-white px-4 py-2.5 text-sm font-semibold text-indigo-700 shadow-sm transition hover:border-indigo-300 hover:bg-indigo-50"
        >
          <MessageCircle className="h-4 w-4" />
          Tanya Chatbot
        </button>
      </div>

      {open && (
        <>
          <button
            type="button"
            aria-label="Tutup chatbot"
            onClick={() => setOpen(false)}
            className="fixed inset-0 z-40 cursor-default bg-slate-950/40"
          />
          <aside
            id="chatbot-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="chatbot-title"
            className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-2xl"
          >
            <header className="flex items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 text-indigo-700">
                  <Bot className="h-5 w-5" />
                </span>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-indigo-600">
                    Asisten analisis spam
                  </p>
                  <h2 id="chatbot-title" className="mt-0.5 text-lg font-bold text-slate-900">
                    Tanya chatbot
                  </h2>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Tutup chatbot"
                className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
              >
                <X className="h-5 w-5" />
              </button>
            </header>

            <div className="flex min-h-0 flex-1 flex-col px-5 pb-5">
              <div className="mt-4 min-h-0 flex-1 space-y-3 overflow-y-auto rounded-xl bg-slate-50 p-3">
                {!messages.length && (
                  <div className="flex items-start gap-2 p-2 text-sm text-slate-500">
                    <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600" />
                    <p>
                      Tanyakan pola spam, akun, keyword, atau statistik komentar judol.
                    </p>
                  </div>
                )}
                {messages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={`flex items-start gap-2 ${
                      message.role === 'user' ? 'justify-end' : ''
                    }`}
                  >
                    {message.role === 'assistant' && (
                      <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700">
                        <Bot className="h-4 w-4" />
                      </span>
                    )}
                    <p
                      className={`max-w-[85%] whitespace-pre-wrap rounded-xl px-3 py-2 text-sm leading-6 ${
                        message.role === 'user'
                          ? 'bg-indigo-600 text-white'
                          : 'bg-white text-slate-700 shadow-sm'
                      }`}
                    >
                      {message.content}
                    </p>
                    {message.role === 'user' && (
                      <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-200 text-slate-600">
                        <UserRound className="h-4 w-4" />
                      </span>
                    )}
                  </div>
                ))}
                {isPending && (
                  <div className="flex items-center gap-2 p-2 text-sm text-slate-500">
                    <Bot className="h-4 w-4 animate-pulse text-indigo-600" />
                    Chatbot sedang menganalisis…
                  </div>
                )}
              </div>

              {error && (
                <div className="mt-3 flex items-start justify-between gap-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                  <span>
                    {error instanceof ApiError
                      ? error.message
                      : 'Chatbot tidak dapat memproses pertanyaan.'}
                  </span>
                  <button type="button" onClick={reset} aria-label="Tutup pesan error">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}

              <div className="mt-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Pertanyaan cepat
                </p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {SUGGESTIONS.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => void sendQuestion(suggestion)}
                      disabled={isPending}
                      className="group flex min-h-16 w-full min-w-0 items-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50/80 px-3 py-2.5 text-left text-xs font-medium leading-5 text-indigo-700 transition hover:-translate-y-0.5 hover:border-indigo-300 hover:bg-indigo-100 hover:shadow-sm disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
                    >
                      <MessageCircle className="h-4 w-4 shrink-0 text-indigo-500 transition group-hover:text-indigo-700" />
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>

              <form onSubmit={submit} className="mt-4 flex gap-2">
                <input
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Tulis pertanyaan tentang komentar…"
                  maxLength={2000}
                  className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                  disabled={isPending}
                />
                <button
                  type="submit"
                  disabled={!question.trim() || isPending}
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Send className="h-4 w-4" />
                  <span className="hidden sm:inline">Kirim</span>
                </button>
              </form>
            </div>
          </aside>
        </>
      )}
    </>
  );
}

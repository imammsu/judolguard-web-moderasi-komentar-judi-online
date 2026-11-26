# JudolGuard

Sistem moderasi komentar judi online (judol) YouTube berbasis AI. Pengguna login dengan Google, memilih video, menekan **Scan**, lalu komentar diklasifikasikan ke tiga zona (judol, perlu review, bukan judol) oleh model TF-IDF + SVM terkalibrasi. **AI memberi rekomendasi, manusia memutuskan.**

Dokumen lengkap: [docs/PRD_JudolGuard_v2.md](docs/PRD_JudolGuard_v2.md).

| Komponen | Teknologi |
|---|---|
| Backend | Python 3.12, Flask 3, Flask-SQLAlchemy, Flask-Migrate, Authlib |
| ML | scikit-learn **1.6.1** (dikunci), joblib, `normalizer.py`, `rules.py` |
| Database | PostgreSQL di Supabase (Session Mode Pooler) — mulai Part 3 |
| Frontend | React 19 + TypeScript, Vite, Tailwind CSS v4, React Router, TanStack Query |
| LLM | Gemini (utama), Groq (cadangan) — mulai Part 7 |

## Prasyarat

- Python **3.12** (diuji 3.12.10)
- Node.js **≥ 20** (diuji 22.14) dan npm
- Windows PowerShell (skrip `.ps1`); di macOS/Linux jalankan perintah yang setara secara manual

## Menjalankan (pengembangan)

Buka dua terminal di root repositori:

```powershell
# Terminal 1 - backend Flask di http://127.0.0.1:5000
.\run-backend.ps1

# Terminal 2 - frontend Vite di http://localhost:5173
.\run-frontend.ps1
```

Buka http://localhost:5173. Beranda menampilkan **"Backend terhubung"** beserta status model ML.
Saat pertama kali dijalankan, skrip otomatis membuat virtualenv / `node_modules`.

> Bila PowerShell menolak menjalankan skrip, jalankan sekali: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Perintah lain:

```powershell
.\run-backend.ps1 -Test        # pytest backend
.\run-frontend.ps1 -Build      # build produksi ke frontend/dist (disajikan Flask di :5000)
cd backend; .\.venv\Scripts\ruff check .   # lint Python
cd frontend; npm run lint; npm run typecheck
```

## Struktur

```
backend/
  app/
    __init__.py        application factory (memuat model sekali, menyajikan frontend/dist)
    config.py          konfigurasi dari .env
    blueprints/        health, auth, videos, comments, keywords, chat, tasks
    ml/
      normalizer.py    prepare() = normalisasi + masking brand (JANGAN diubah tanpa latih ulang)
      rules.py         aturan "bukan" -> "review"
      loader.py        singleton model + classify_array()
      model/           judol_model.joblib, metrics.json
  tests/
frontend/src/          pages, components, api, hooks, types
docs/                  PRD
notebooks/             notebook training & evaluasi
```

> `backend/app/ml/normalizer.py` dicek hash SHA-256-nya saat startup. Bila isinya berubah, `/health` melaporkan `normalizer_match: false`. Perubahan normalizer wajib diikuti latih ulang model dan pembaruan `metrics.json` (Part 9).

## Mengisi `.env`

File `.env` di root sudah dibuat dari `.env.example` dengan kredensial **kosong**. Aplikasi Part 1 tetap berjalan tanpa kredensial. Isi bertahap sesuai part:

### 1. `SECRET_KEY` dan `FERNET_KEY` (isi sekarang)

```powershell
cd backend
.\.venv\Scripts\python -c "import secrets; from cryptography.fernet import Fernet; print('SECRET_KEY=' + secrets.token_hex(32)); print('FERNET_KEY=' + Fernet.generate_key().decode())"
```

Salin kedua baris hasilnya ke `.env`. Jangan ganti `FERNET_KEY` setelah ada token tersimpan di database (token lama tidak bisa didekripsi).

### 2. `GOOGLE_CLIENT_ID` dan `GOOGLE_CLIENT_SECRET` (Part 2)

1. Buka https://console.cloud.google.com/ → buat project baru.
2. **APIs & Services → Library** → aktifkan **YouTube Data API v3**.
3. **OAuth consent screen** → User type **External**, status **Testing** → tambahkan scope `https://www.googleapis.com/auth/youtube.force-ssl` → tambahkan email Anda dan dosen penguji di **Test users**.
4. **Credentials → Create credentials → OAuth client ID** → tipe **Web application** → Authorized redirect URIs:
   - `http://localhost:5173/auth/callback`
   - `http://127.0.0.1:5000/auth/callback`
5. Salin Client ID dan Client secret ke `.env`. `GOOGLE_REDIRECT_URI` biarkan `http://localhost:5173/auth/callback` selama pengembangan.

### 3. `DATABASE_URL` Supabase (Part 3)

1. Buka https://supabase.com/dashboard → buat project (simpan password database).
2. Klik **Connect** → pilih **Session pooler** (port **5432**, host `aws-0-<region>.pooler.supabase.com`).
3. Salin URI, ganti `[YOUR-PASSWORD]` dengan password database:
   ```
   DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
   ```
   Backend otomatis memakai driver `psycopg` v3. Bila password mengandung karakter khusus (`@`, `#`, `/`), encode dulu (mis. `@` → `%40`).
4. **Jangan** memakai kunci `anon`/`service_role` Supabase — aplikasi hanya butuh `DATABASE_URL`.

### 4. `GEMINI_API_KEY` dan `GROQ_API_KEY` (Part 7–8)

- Gemini: https://aistudio.google.com/apikey → **Create API key**.
- Groq: https://console.groq.com/keys → **Create API Key**.

Setelah mengubah `.env`, restart backend. Status tiap kredensial terlihat di kartu **Konfigurasi (.env)** pada beranda.

### 5. JudolGuard Sentinel (Telegram)

Sentinel akan menjalankan bot Telegram dan scheduler patroli sebagai worker
terpisah pada tahap implementasi berikutnya. Konfigurasi dasarnya:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEB_BASE_URL=http://localhost:5173
SENTINEL_ENABLED=false
SENTINEL_POLL_INTERVAL_SECONDS=300
SENTINEL_MAX_VIDEOS=5
PAIRING_TOKEN_TTL_SECONDS=600
SENTINEL_MIN_ALERT_COUNT=1
TELEGRAM_MAX_MESSAGES_PER_MINUTE=10
TELEGRAM_POLLING_TIMEOUT=30
```

Untuk deployment, jalankan API Flask dan Sentinel Worker sebagai proses
terpisah pada hosting yang mendukung proses selalu aktif seperti Railway atau
Render Background Worker. Scheduler tidak boleh dijalankan di setiap instance
API agar satu siklus patroli tidak berjalan ganda.

Pada Tahap 2, worker Telegram dapat diuji secara lokal dengan:

```powershell
cd backend
$env:TELEGRAM_BOT_TOKEN="TOKEN_DARI_BOTFATHER"
$env:SENTINEL_ENABLED="true"
.venv\Scripts\python.exe sentinel_worker.py
```

Token bot dibuat melalui akun `@BotFather` di Telegram menggunakan perintah
`/newbot`. Simpan token hanya di environment variable dan jangan commit ke Git.

## Aturan commit & branch

- Branch: `main` (stabil, tiap part ditandai tag `v0.x`), `part-N-nama` untuk pengerjaan per part.
- Pesan commit: [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`.
- Jangan pernah commit `.env`, `node_modules/`, `.venv/`, atau `frontend/dist/`.

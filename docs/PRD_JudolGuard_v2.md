# Product Requirements Document (PRD)

## JudolGuard: Sistem Moderasi Komentar Judi Online YouTube Berbasis AI

| | |
|---|---|
| **Mata kuliah** | Praktik Aplikasi Web (Smart Web) |
| **Versi dokumen** | 2.4 |
| **Status** | Dalam pengerjaan (Part 0 selesai) |
| **Penyusun** | _(isi nama/NIM)_ |
| **Terakhir diperbarui** | 18 November 2026 |

### Riwayat Perubahan

**v2.4** (resolusi pertanyaan terbuka, optimasi alur scan & batching, dan spesifikasi artefak model)
- Ditetapkan: koneksi database Supabase menggunakan **Session Mode Pooler** (port `5432`).
- Ditetapkan: angka retensi data final **30 hari**; apabila pengguna login kembali setelah melewati 30 hari, sistem menghapus data kedaluwarsa, melakukan hit YouTube API lagi, dan menyimpan ulang ke database.
- Diperbarui alur hemat kuota dan klasifikasi: **saat pengguna mengklik video, komentar belum langsung dimuat/ditampilkan**; komentar baru diambil secara *batch* (`maxResults=100`, *bulk upsert*) saat pengguna menekan tombol **Scan**, lalu keseluruhan komentar langsung diproses dan diklasifikasikan sekaligus sebagai **satu array tervektorisasi** (`model.predict_proba(array)`) sehingga yang tampil di layar langsung berupa komentar yang sudah terklasifikasi.
- Ditetapkan strategi hemat kuota `comments.setModerationStatus` menggunakan **multi-ID batching** (mengirimkan kumpulan `comment_id` dipisahkan koma hingga 50 ID per panggilan API).
- Ditambahkan rincian dimensi fitur aktual dari artefak `judol_model.joblib` (92.561 fitur: 34.046 word n-gram + 58.515 char n-gram) dan hash SHA-256 `normalizer.py`.

**v2.3** (keputusan teknis dan kebijakan data)
- Ditetapkan: UI **Tailwind CSS**; LLM **Gemini sebagai utama, Groq sebagai cadangan, lalu pesan "analisis AI tidak tersedia"**; Docker tidak dipakai; frontend React disajikan dari Flask.
- Ditambahkan 10.3 (rantai cadangan LLM) dan kebijakan retensi data (14.2) beserta tugasnya di Part 9.
- Kolom target tanggal dihapus dari papan progres.
- Bagian 19 dipisah menjadi keputusan yang sudah diambil dan pertanyaan yang masih terbuka.

**v2.2** (pembagian part baru dan Supabase)
- Pengerjaan dibagi menjadi **10 part** dengan urutan baru: Fondasi Aplikasi, OAuth Login, Database Supabase, Pengambilan Video dan Komentar, Klasifikasi dan Review, Reject Komentar, Ekstraksi Kata Kunci, Chatbot, Perbaikan, serta Deploy dan Finalisasi.
- Database ditetapkan sebagai **PostgreSQL di Supabase**, lengkap dengan catatan jenis koneksi, RLS, dan batas tier gratis.
- **Halaman evaluasi model dihapus dari aplikasi web.** Metrik disajikan di laporan dan notebook; endpoint `/api/model/metrics` dan Blueprint `model` ikut dihapus.
- Tabel dimigrasikan bertahap per part; tabel `videos` pindah dari awal ke Part 4 bersama `comments` dan `jobs`.

**v2.1**
- Tech stack ditetapkan: PostgreSQL, Flask, dan React + TypeScript.
- Ditambahkan struktur repositori, rancangan tugas latar belakang di Flask, dan catatan integrasi cookie/CORS.
- Bagian YouTube API diperbarui berdasarkan dokumentasi resmi: model kuota, `part`/`fields`, ETag, gzip, dan strategi hemat kuota.

**v2.0**
- Klasifikasi memakai TF-IDF + SVM terkalibrasi dengan pintu masuk teks `prepare()` dan masking brand.
- Metrik dan batasan model diisi dari hasil training dan evaluasi aktual (`metrics.json`).
- Ditambahkan lapisan aturan dan pengecekan hash normalizer.
- Clustering dan ringkasan visual tetap di luar lingkup.

---

## 1. Ringkasan Eksekutif

JudolGuard adalah aplikasi web cerdas untuk membantu pemilik channel YouTube memoderasi komentar judi online (judol). Pengguna login dengan akun Google, memilih video, lalu sistem mengambil komentarnya dan mengklasifikasikannya dengan model machine learning (TF-IDF + SVM). Hasilnya ditampilkan dalam tiga zona (judol, perlu review, bukan judol) untuk ditinjau pengguna sebelum di-reject. Dari komentar judol, LLM mengekstrak nama situs dan kata kunci yang siap disalin ke fitur *Blocked words* YouTube Studio. Pengguna juga dapat bertanya ke chatbot tentang akun atau pola spam, dan chatbot menjawab dari data di database.

Prinsip utama: **AI memberi rekomendasi, manusia memutuskan.** Sistem tidak pernah me-reject komentar secara otomatis.

---

## 2. Latar Belakang dan Masalah

Komentar judol membanjiri kolom komentar YouTube. Masalah yang dihadapi content creator:

1. **Pengaburan teks.** Pelaku memakai huruf Unicode bergaya (𝗚𝗔𝗖𝗢𝗥), angka pengganti huruf, spasi atau simbol sisipan, dan nama situs yang terus berganti, sehingga lolos dari filter bawaan.
2. **Moderasi manual melelahkan.** Ratusan komentar per video harus ditinjau dan di-reject satu per satu.
3. **Daftar *Blocked words* sulit disusun.** Creator tidak tahu kata atau nama situs apa yang sedang dipakai spammer.
4. **Tidak ada gambaran pelaku.** Sulit mengetahui akun mana yang paling sering menyebar spam.

---

## 3. Tujuan dan Metrik Keberhasilan

### 3.1 Tujuan

1. Mempercepat moderasi komentar judol pada video YouTube.
2. Menghasilkan daftar kata kunci akurat untuk *Blocked words* YouTube Studio.
3. Memberi insight tentang akun penyebar spam melalui chatbot berbasis data.
4. Menekan risiko salah reject lewat skema tiga zona dan review manual.

### 3.2 Metrik Model (Hasil Aktual dari Training)

| Metrik | Nilai | Keterangan |
|---|---|---|
| Precision judol (test) | 0,981 | 8 salah label dari 4.202 komentar normal |
| Recall judol (test) | 0,955 | 20 judol terlewat dari 442 |
| F1 judol (test) | 0,968 | |
| PR-AUC (test) | 0,978 | |
| F1 leave-brand-out, dengan masking brand | ≈ 0,96 | Tanpa masking ≈ 0,86 (uji pada brand yang tidak ada di data latih) |
| F1 uji eksternal (live chat Jogja) | 0,794 | Precision 0,758, recall 0,833, PR-AUC 0,719; hanya 30 judol unik |
| Ukuran model | ± 2,9 MB | Muat di hosting gratis dan repositori GitHub tanpa LFS |

Metrik ini disajikan di laporan dan notebook, bukan di halaman web aplikasi.

### 3.3 Target Tambahan untuk Aplikasi

- **Precision zona "judol" ≥ 0,95** pada data uji (menekan salah reject).
- **Uji pada komentar nyata YouTube** (minimal 150 komentar berlabel manual, dilabeli sebelum melihat prediksi model): hasil dilaporkan beserta rentang kepercayaan.
- **Waktu klasifikasi** 1.000 komentar kurang dari 10 detik (tanpa pengambilan dari YouTube).
- **Validitas kata kunci**: 100% kata kunci yang ditampilkan ada di teks asli komentar sumber.
- **Akurasi pemilihan tool chatbot** ≥ 85% pada 30 pertanyaan uji.
- **Nol salah label** pada daftar uji *hard negative* (komentar normal berisi nama produk, tahun, atau game seperti `iphone15`, `yamaha125`, `season18`), setelah perbaikan masking di Part 9.

---

## 4. Pengguna dan Skenario

### 4.1 Persona

- **Content creator / pemilik channel (pengguna utama).** Punya video dengan komentar judol, tidak punya latar belakang teknis, ingin proses cepat dan aman.
- **Dosen/penguji (pengguna uji).** Mengevaluasi fungsi dan kualitas sistem; didaftarkan sebagai *test user* OAuth.

### 4.2 Skenario Utama

1. Creator login, memilih video yang banyak spam (saat baru memilih video, komentar belum langsung dimuat agar hemat kuota), menekan tombol "Scan & Klasifikasi", melihat keseluruhan komentar yang langsung tampil dalam tiga zona klasifikasi, meninjau hasil, me-reject komentar judol secara batch, lalu menyalin kata kunci ke YouTube Studio.
2. Creator bertanya ke chatbot, "Akun mana yang paling sering spam?", dan mendapat daftar akun beserta jumlah komentarnya.

---

## 5. Ruang Lingkup

### 5.1 Dalam Lingkup

- Login OAuth Google/YouTube.
- Penyimpanan data (pengguna, video, komentar, hasil klasifikasi, kata kunci) di PostgreSQL pada Supabase.
- Daftar video channel pengguna.
- Pengambilan komentar utama (top-level) dan penyimpanan ke database.
- Klasifikasi komentar judol (TF-IDF + SVM terkalibrasi) dengan zona tiga tingkat dan lapisan aturan.
- Review hasil klasifikasi dan koreksi label manual.
- Reject komentar (satuan, terpilih, semua judol).
- Ekstraksi nama situs dan kata kunci judol dengan LLM, divalidasi di kode.
- Chatbot analisis spam (LLM tool calling, jawaban berbasis template).

### 5.2 Di Luar Lingkup

- **Clustering komentar** dan **dashboard ringkasan visual** (fungsinya sudah dicakup ekstraksi kata kunci dan chatbot).
- **Halaman evaluasi model di aplikasi web** (hasil evaluasi disajikan di laporan dan notebook).
- Penghapusan permanen komentar (YouTube API hanya menyediakan status moderasi `rejected`).
- Moderasi otomatis tanpa review manusia.
- Moderasi komentar di channel milik orang lain.
- Analisis balasan (reply) pada versi 1.
- Pelatihan ulang model otomatis di dalam aplikasi.
- Pemakaian layanan Supabase selain database (Auth, Storage, dan klien JS di frontend).
- Aplikasi mobile native.

---

## 6. Fitur Utama

1. **Login OAuth YouTube**
   Pengguna masuk dengan akun Google dan memberikan izin akses komentar serta moderasi. Scope: `youtube.force-ssl`. Token disimpan di server (refresh token terenkripsi di database), sesi memakai cookie `HttpOnly`, dan pengguna dapat logout.

2. **Daftar video channel**
   Menampilkan video milik pengguna (judul, thumbnail, tanggal, jumlah komentar). Diambil lewat playlist *uploads* (`channels.list`, `playlistItems.list`, `videos.list`) agar hemat kuota, dengan paginasi, dan disimpan di database sebagai cache.

3. **Pengambilan komentar secara batch (saat tombol Scan ditekan)**
   Saat pengguna mengklik video, komentar **belum langsung diambil atau ditampilkan** untuk menghemat kuota (kecuali video tersebut sudah pernah di-scan dalam masa retensi < 30 hari). Ketika pengguna menekan tombol **"Scan Komentar"**, sistem mengambil komentar utama secara *batch* dengan paginasi (`maxResults=100` per halaman, penghentian inkremental bila bertemu komentar yang sudah tersimpan) dan menyimpannya ke PostgreSQL dengan *bulk upsert* berdasarkan `comment_id`. Disimpan: teks asli utuh, nama penulis, `author_channel_id`, waktu, dan jumlah like. Ada batas maksimum komentar per pengambilan dan indikator progres.

4. **Klasifikasi komentar judol sekaligus dalam satu array**
   Begitu pengambilan batch selesai dalam alur Scan, seluruh komentar yang belum diklasifikasi dikumpulkan menjadi **satu array**, diproses secara batch oleh `prepare()` (normalisasi + masking brand), dideduplikasi berdasarkan `text_hash`, lalu seluruh array teks unik dinilai sekaligus dalam **satu kali pemanggilan `model.predict_proba(array)`**. Hasil dibagi tiga zona berdasarkan ambang `t_low` dan `t_high` dari `metrics.json`. Lapisan aturan menaikkan komentar berpola iklan dari "bukan" menjadi "perlu review". Disimpan secara *bulk*: zona, skor, penanda aturan, versi model, dan waktu. Setelah selesai, halaman langsung menampilkan keseluruhan komentar yang sudah terklasifikasi.

5. **Review dan reject komentar**
   Tabel hasil dengan filter zona, pencarian, dan pengurutan berdasarkan skor. Pengguna meninjau hasil dan dapat mengoreksi label ("tandai bukan judol / judol"). Reject satu per satu, beberapa yang dipilih, atau semua judol menggunakan strategi **multi-ID batching** (mengirim hingga 50 `comment_id` dipisahkan koma dalam satu panggilan `comments.setModerationStatus` agar hemat kuota), dengan konfirmasi yang menampilkan jumlah komentar dan perkiraan kuota API. Tidak ada reject otomatis.

6. **Ekstraksi kata kunci judol**
   LLM mengekstrak nama situs dan kata khas dari komentar berlabel judol (teks asli, tanpa nama akun). Kode memvalidasi bahwa setiap kata ada di teks asli, menghitung frekuensi, dan menyaring kata umum. Pengguna memilih kata dengan checkbox, lalu menyalinnya dalam format dipisah koma untuk *Blocked words* YouTube Studio.

7. **Chatbot analisis spam**
   Pengguna bertanya bebas. LLM memilih tool (tool calling), backend menjalankan query ke database, dan jawaban disusun dari template. Pertanyaan di luar cakupan ditangani fallback. Tersedia tombol pertanyaan siap pakai yang memanggil fungsi langsung tanpa LLM.

---

## 7. Alur Pengguna

1. **Login** dengan akun Google (OAuth YouTube) dan memberikan izin (jika data tersimpan pengguna sudah melewati masa retensi 30 hari, sistem membersihkan data kedaluwarsa dan me-refresh dari API).
2. **Melihat daftar video** di channel.
3. **Memilih satu video**: halaman menampilkan informasi video tanpa langsung memuat komentar mentah dari YouTube API (kecuali hasil klasifikasi sebelumnya masih tersimpan dan berusia < 30 hari).
4. **Menekan tombol "Scan Komentar"** dan menunggu progres selesai: sistem mengambil komentar secara *batch* (`maxResults=100` per halaman) lalu langsung mengklasifikasikan keseluruhan komentar sekaligus dalam satu array.
5. **Melihat hasil klasifikasi**: keseluruhan komentar langsung tampil dikelompokkan menjadi tiga zona (`judol`, `perlu review`, dan `bukan judol`).
6. **Meninjau hasil dan mengoreksi label** bila ada yang salah.
7. **Me-reject komentar** (satuan, terpilih, atau semua judol secara *multi-ID batch*) setelah konfirmasi.
8. **Mengambil kata kunci**: memilih kata dengan checkbox, menekan Copy, lalu menempelkannya ke YouTube Studio.
9. **Bertanya ke chatbot** tentang akun atau pola spam.

---

## 8. Arsitektur Sistem

### 8.1 Tech Stack

- **Database**: **PostgreSQL di Supabase** (PostgreSQL terkelola, tier gratis). Supabase hanya dipakai sebagai database: akses lewat SQLAlchemy dan migrasi dengan Alembic (Flask-Migrate), tanpa Supabase Auth, Storage, maupun klien JS.
- **Backend**: Python **Flask** (application factory dengan Blueprint per modul), dijalankan dengan Gunicorn di produksi.
  - ORM: Flask-SQLAlchemy dan Flask-Migrate; driver `psycopg` (v3) atau `psycopg2-binary`.
  - OAuth dan YouTube: Authlib (Google OAuth 2.0) dan `google-api-python-client` (YouTube Data API v3).
  - Sesi: cookie `HttpOnly`; token OAuth disimpan di server.
  - Validasi masukan: Pydantic atau Marshmallow.
  - Keamanan: Flask-Limiter (rate limit), Flask-CORS bila origin berbeda, `cryptography` (Fernet) untuk mengenkripsi refresh token.
  - Tugas latar belakang: pekerja berbasis tabel `jobs` di PostgreSQL (lihat 8.7).
  - ML: scikit-learn 1.6.1, joblib, NumPy, serta `normalizer.py` dan `rules.py`.
- **Frontend**: **React + TypeScript** dengan Vite.
  - Routing: React Router.
  - Data dan polling status tugas: TanStack Query.
  - Klien API bertipe: `fetch` atau Axios dengan tipe TypeScript untuk setiap respons.
  - UI: **Tailwind CSS**.
- **LLM eksternal**: **Gemini API** sebagai penyedia utama, **Groq API** sebagai cadangan, dan pesan statis "analisis AI tidak tersedia" bila keduanya gagal (lihat 10.3).
- **Sumber data**: YouTube Data API v3.
- **Perkakas**: Git/GitHub, variabel lingkungan (`.env`), dan GitHub Actions untuk uji otomatis (opsional). Docker tidak diperlukan: database memakai Supabase dan Flask berjalan langsung di virtualenv.

Yang ditetapkan adalah PostgreSQL (Supabase), Flask, React TypeScript, dan Tailwind CSS; pustaka pendukung lain adalah saran.

### 8.2 Alur Teknis Scan (Batch Fetch & Klasifikasi Satu Array)

1. Saat pengguna memilih video, sistem mengecek apakah komentar terklasifikasi sudah ada di database dan masih dalam masa retensi (< 30 hari). Komentar **tidak** diambil otomatis saat klik video.
2. Saat pengguna menekan tombol **Scan**, sistem mengambil komentar dari YouTube Data API v3 secara *batch* dengan paginasi (`maxResults=100` per halaman, berhenti lebih awal bila bertemu `comment_id` yang sudah ada).
3. *Bulk upsert* seluruh batch komentar ke database PostgreSQL (`INSERT ... ON CONFLICT (comment_id) DO UPDATE`, menyimpan teks asli utuh).
4. Ambil seluruh komentar pada video tersebut yang belum diklasifikasi dan kumpulkan menjadi **satu array/list** di memori.
5. Jalankan `[prepare(teks) for teks in array]` untuk menghasilkan array teks masukan model; deduplikasi berdasarkan `text_hash` (SHA-256 dari teks hasil `prepare()`).
6. Panggil `model.predict_proba(unique_prepared_array)` **satu kali untuk keseluruhan array teks unik** sekaligus; terapkan ambang `t_low` dan `t_high`.
7. Lapisan aturan (`rules.py`): komentar di zona "bukan" yang memenuhi pola iklan dinaikkan ke "perlu review".
8. Hasil dari tiap teks unik dipetakan kembali ke semua duplikatnya, dilakukan *bulk update* ke database (zona, skor, penanda aturan, versi model, waktu), lalu UI menampilkan keseluruhan komentar yang sudah terklasifikasi.

### 8.3 Alur Ekstraksi Kata Kunci

1. Ambil komentar berlabel judol, deduplikasi, dan kirim ke LLM secara batch (20-50 komentar, tanpa nama akun).
2. LLM mengembalikan JSON berisi nama situs dan kata kunci per komentar.
3. Kode memvalidasi struktur, ID, dan keberadaan kata di teks asli; menghitung frekuensi dan menyaring kata umum.
4. Hasil disimpan sebagai cache dan ditampilkan dengan tombol Copy.

### 8.4 Alur Chatbot

1. Pengguna mengirim pertanyaan.
2. Backend mengirim pertanyaan dan definisi tool ke LLM.
3. LLM memilih tool dan parameter (tidak mengeksekusi apa pun).
4. Backend memvalidasi nama tool (whitelist) dan parameter, lalu menjalankan query dengan identitas dari sesi.
5. Jawaban disusun dari template berdasarkan hasil query.
6. Jika tidak ada tool yang cocok, fallback.

### 8.5 Pembagian Peran

- **Model SVM**: klasifikasi judol atau bukan.
- **LLM**: ekstraksi nama situs/kata kunci dan pemilihan tool chatbot.
- **Kode backend**: normalisasi, dedup, threshold, aturan, validasi, agregasi, query database, dan template jawaban.

---

### 8.6 Struktur Repositori

```
judolguard/
├── backend/
│   ├── app/
│   │   ├── __init__.py        (application factory, memuat model sekali)
│   │   ├── config.py
│   │   ├── extensions.py      (db, migrate, limiter, oauth)
│   │   ├── models/            (model SQLAlchemy)
│   │   ├── blueprints/        (auth, videos, comments, keywords, chat, tasks)
│   │   ├── repositories/      (lapisan query ke database)
│   │   ├── services/          (youtube, classifier, extractor, chatbot_tools, jobs)
│   │   └── ml/                (normalizer.py, rules.py, model/judol_model.joblib, metrics.json)
│   ├── migrations/
│   ├── tests/
│   ├── requirements.txt
│   └── wsgi.py
├── frontend/
│   ├── src/                   (pages, components, api, hooks, types)
│   ├── package.json
│   └── vite.config.ts
├── notebooks/                 (notebook training dan evaluasi)
├── docs/                      (PRD, laporan)
├── .env.example
└── README.md
```

### 8.7 Catatan Integrasi Flask, React, dan Supabase

- **Model dimuat sekali per proses** di application factory dan disimpan sebagai singleton. Gunicorn dengan beberapa worker memuat satu salinan per worker (model ± 2,9 MB, aman).
- **Tugas latar belakang.** Flask tidak punya background task bawaan. Rancangan sederhana: endpoint membuat baris di tabel `jobs` (status `queued`, `running`, `done`, `failed`, beserta progres), lalu `ThreadPoolExecutor` menjalankannya. Frontend melakukan polling `/api/tasks/{id}` lewat TanStack Query. Saat aplikasi restart, job berstatus `running` ditandai ulang saat startup. Setiap job dirancang **idempoten** (upsert, hanya memproses komentar yang belum diklasifikasi) karena hosting gratis dapat menidurkan atau me-restart proses. Bila kelak butuh skala, ganti ke RQ atau Celery tanpa mengubah kontrak API.
- **Penyajian frontend dan cookie.** Saat pengembangan, React berjalan di server Vite dan meneruskan (proxy) permintaan `/api` dan `/auth` ke Flask. Saat produksi, `npm run build` menghasilkan berkas statis di `frontend/dist`, dan **Flask menyajikan berkas itu** (folder statis ditambah satu route penampung agar React Router berfungsi saat halaman dimuat ulang). Hasilnya satu deployment dan satu origin, sehingga cookie `HttpOnly` dan `SameSite=Lax` bekerja tanpa konfigurasi CORS yang rumit. Bila frontend dipisah ke hosting lain, atur CORS dengan `supports_credentials`, cookie `SameSite=None; Secure`, dan token CSRF.
- **Kontrak API.** Respons JSON seragam; tipe TypeScript di `frontend/src/types` mencerminkan skema respons dan dijaga sinkron dengan backend.
- **Keamanan tampilan.** Isi komentar tidak tepercaya. Render sebagai teks biasa dan jangan memakai `dangerouslySetInnerHTML`, untuk mencegah XSS.
- **Database.** Upsert dengan `INSERT ... ON CONFLICT (comment_id) DO UPDATE`; pencarian teks dengan `ILIKE` dan indeks `pg_trgm` bila diperlukan; tipe waktu `TIMESTAMPTZ`. Detail koneksi Supabase ada di 11.3.

## 9. Spesifikasi Machine Learning

### 9.1 Dataset

- **Data latih**: komentar YouTube berlabel hasil scraping dan penggabungan beberapa sumber. Setelah dedup: **32.626 komentar** (judol 3.117, normal 29.509, prevalensi judol 9,55%), dalam 27.362 kelompok kalimat mirip.
- **Data uji eksternal**: dataset live chat Jogja (tidak dipakai untuk training), 2.543 komentar unik dengan 30 judol.
- **Kolom yang dipakai model**: hanya teks komentar. Kolom lain (`author`, `tanggal`, `video_id`, `channel`, `predicted_label`, `komentar_clean`) tidak dipakai sebagai fitur.
- **Catatan**: sumber dan lisensi tiap dataset dicantumkan di Lampiran A.

### 9.2 Pra-pemrosesan (`prepare()`)

1. Unicode NFKC, penghapusan tanda gabung dan karakter tak terlihat, lowercase.
2. Pemetaan huruf mirip (Yunani/Sirilik) dan angka dingbat ke Latin.
3. Penghapusan `@mention` dan kode emoji; penggantian URL dan nomor telepon dengan token.
4. Penggabungan huruf tunggal berderet (`g a c o r` menjadi `gacor`), pemetaan leetspeak di antara huruf, perapian huruf berulang.
5. **Masking brand**: nama situs judol diganti `brandtoken` agar model mengenali brand baru yang belum pernah dilihat.

**Aturan keras:** model hanya valid untuk masukan hasil `prepare()`. Uji menunjukkan bahwa memakai `normalize()` saja menurunkan F1 eksternal dari 0,79 menjadi 0,06.

### 9.3 Model

- **Fitur**: `FeatureUnion` TF-IDF gabungan word n-gram (`ngram_range=(1, 2)`, `min_df=2`, `max_features=50000`, `sublinear_tf=True` → **34.046 fitur**) dan char n-gram (`analyzer="char_wb"`, `ngram_range=(2, 5)`, `min_df=2`, `max_features=100000`, `sublinear_tf=True` → **58.515 fitur**), menghasilkan total **92.561 dimensi fitur**.
- **Classifier**: `LinearSVC(C=5.0, class_weight="balanced", max_iter=5000)`, dikalibrasi dengan `CalibratedClassifierCV(method="sigmoid", cv=5)` per kelompok kalimat mirip.
- **Inferensi Batch (Satu Array)**: Seluruh komentar unik hasil `prepare()` diprediksi sekaligus dalam satu pemanggilan `model.predict_proba(array_teks_unik)` agar vektorisasi TF-IDF dan perkalian matriks SVM berjalan tervektorisasi di NumPy/SciPy.
- **Split**: `StratifiedGroupKFold` per kelompok kalimat mirip (train 22.840, val 5.142, test 4.644), agar kerangka kalimat yang sama tidak berada di train dan test sekaligus.
- **Threshold**: `t_low = 0,235` (`0.2351288665553617`), `t_high = 0,5` (disimpan di `metrics.json`, dibaca aplikasi saat startup).
- **Versi**: `scikit-learn==1.6.1` harus dikunci di `requirements.txt`.

### 9.4 Lapisan Aturan

- Tujuan: menutup jenis spam yang tidak ada di data latih, yaitu iklan tanpa brand ("info link gacor", "ketik di google", "bonus chip gratis") dan pola kontak + ajakan (WA/Telegram/link + bonus/daftar).
- Perilaku: **hanya menaikkan "bukan" menjadi "perlu review"**, tidak pernah menolak otomatis, karena aturan bisa menjerat keluhan penonton.
- Evaluasi: diukur terpisah (jumlah judol yang tertolong dan jumlah normal yang ikut terjaring) pada data uji eksternal dan data nyata.

### 9.5 Batasan Model yang Diketahui

- **Masking brand salah sasaran.** Pola huruf + 2-3 digit dan akhiran `win` dapat menyamarkan kata normal (`iphone15`, `yamaha125`, `covid19`, `darwin`, `film 4d`), sehingga komentar normal bisa dinilai judol. Di data uji tingkat kejadiannya rendah (0,1-0,2% komentar normal), tetapi dapat lebih sering di channel teknologi, game, atau otomotif. Perbaikan dijadwalkan di Part 9.
- **Brand dengan pola penamaan baru** (misalnya `BWTOGEL`) dapat lolos dari masking.
- **Iklan tanpa brand** ("slot gacor", "info link gacor") mendapat skor rendah; ditangani lapisan aturan.
- **Komentar keluhan** yang menyebut nama situs ("blokir wisdomtoto") dapat dinilai judol.
- **Uji eksternal berukuran kecil** (30 judol): recall 25/30 (rentang 95% ≈ 0,66-0,93), precision 25/33 (≈ 0,59-0,87). Laporkan hitungan dan rentang, bukan hanya F1.

---

## 10. Spesifikasi LLM

### 10.1 Ekstraksi Kata Kunci

- **Model**: Gemini sebagai utama dengan cadangan Groq (lihat 10.3; dikonfigurasi lewat environment variable), temperature 0, output JSON terstruktur.
- **Input**: batch 20-50 komentar judol unik, berisi ID dan teks asli saja (tanpa nama akun).
- **Output per komentar**:

```json
{ "id": "c123", "situs": ["GACOR77"], "kata_kunci": ["gacor77", "maxwin"] }
```

- **Prompt**: instruksi dan data dipisahkan delimiter jelas; isi komentar diperlakukan sebagai data, bukan perintah (mitigasi prompt injection); LLM tidak diberi tool pada tahap ini.
- **Validasi**: jumlah item dan ID cocok, tipe data valid, setiap kata kunci ada di teks asli (substring) dalam bentuk aslinya (misalnya `𝗚𝗔𝗖𝗢𝗥77`); item gagal di-retry dengan backoff.
- **Rate limit**: batching, antrean, retry exponential backoff, cache hasil, dan opsi fallback antar-provider.

### 10.2 Chatbot (Tool Calling)

Tool bersifat read-only, parameter divalidasi, hasil dibatasi (`LIMIT`), dan semua query difilter berdasarkan pemilik data dari sesi login.

- `top_spammers(video_id?, limit?)`: akun dengan komentar judol terbanyak.
- `count_judol(video_id?)`: jumlah dan persentase komentar judol.
- `top_keywords(video_id?, limit?)`: kata kunci/situs judol paling sering.
- `comments_by_author(author, limit?)`: komentar judol dari satu akun.
- `peak_hours(video_id?)`: jam dengan komentar judol terbanyak.
- `duplicate_comments(video_id?, limit?)`: komentar judol yang disalin berulang.
- `compare_videos(limit?)`: video dengan komentar judol terbanyak.

Aturan perilaku: wajib memakai tool untuk pertanyaan berbasis data; tidak menebak angka atau nama akun; data kosong dijawab jujur; pertanyaan di luar cakupan ditangani fallback (tolak sopan atau jawaban umum berlabel "bukan dari data komentarmu"); identitas akun memakai `author_channel_id`.

### 10.3 Rantai Cadangan LLM

- **Urutan penyedia**: Gemini (utama), lalu Groq (cadangan), lalu pesan statis **"analisis AI sedang tidak tersedia"**.
- **Pemicu beralih ke penyedia berikutnya**: timeout, rate limit (HTTP 429), galat server (5xx), atau output JSON yang tetap tidak valid setelah retry.
- **Adapter LLM**: satu antarmuka (`LLMClient`) dengan implementasi Gemini dan Groq. Format function calling kedua penyedia berbeda, jadi adapter menerjemahkan definisi tool ke format masing-masing, sementara validasi output (skema JSON, substring kata, whitelist tool) tetap sama dan dijalankan di kode, bukan di penyedia.
- **Konfigurasi**: urutan penyedia dan API key lewat environment variable; penyedia yang dipakai dicatat di log untuk setiap permintaan.
- **Perilaku saat semua gagal**: ekstraksi kata kunci menampilkan pesan "analisis AI tidak tersedia, coba lagi nanti"; chatbot menampilkan pesan yang sama tetapi tombol pertanyaan siap pakai (tanpa LLM) tetap berfungsi. Klasifikasi, review, dan reject tidak terpengaruh karena tidak memakai LLM.
- **Privasi tetap sama** di kedua penyedia: hanya teks komentar berlabel judol tanpa nama akun yang dikirim.
- **Pengujian**: simulasikan kegagalan penyedia utama (timeout dan 429) dan pastikan aplikasi beralih ke cadangan, lalu ke pesan statis.

---

## 11. Model Data (PostgreSQL di Supabase)

### 11.1 Tabel

**users**
- `id` BIGSERIAL (PK), `channel_id` TEXT (UNIQUE), `email` TEXT, `refresh_token_enc` TEXT (terenkripsi), `created_at` TIMESTAMPTZ default `now()`

**videos**
- `video_id` TEXT (PK), `owner_channel_id` TEXT (FK ke `users.channel_id`), `title` TEXT, `thumbnail_url` TEXT, `published_at` TIMESTAMPTZ, `comment_count` INTEGER, `last_fetched_at` TIMESTAMPTZ

**comments**
- `comment_id` TEXT (PK), `video_id` TEXT (FK), `owner_channel_id` TEXT
- `author_name` TEXT, `author_channel_id` TEXT
- `text_original` TEXT (teks asli utuh), `text_prepared` TEXT, `text_hash` CHAR(64)
- `published_at` TIMESTAMPTZ, `like_count` INTEGER
- `zone` TEXT, CHECK nilai `judol`, `review`, `bukan` (NULL bila belum diklasifikasi)
- `score` REAL, `rule_hit` BOOLEAN default `false`
- `model_version` TEXT, `classified_at` TIMESTAMPTZ
- `user_label` SMALLINT (0 atau 1, NULL bila tidak dikoreksi)
- `moderation_status` TEXT, CHECK nilai `none`, `rejected`, `failed`, default `none`

**keywords**
- `id` BIGSERIAL (PK), `video_id` TEXT, `owner_channel_id` TEXT
- `keyword` TEXT (bentuk asli), `type` TEXT (`situs` atau `kata_kunci`), `frequency` INTEGER, `extracted_at` TIMESTAMPTZ
- UNIQUE (`video_id`, `keyword`)

**moderation_log**
- `id` BIGSERIAL (PK), `owner_channel_id` TEXT, `comment_id` TEXT, `action` TEXT, `status` TEXT, `error` TEXT, `created_at` TIMESTAMPTZ

**jobs**
- `id` UUID (PK), `owner_channel_id` TEXT, `type` TEXT (`scan`, `fetch`, `classify`, `extract`), `video_id` TEXT
- `status` TEXT (`queued`, `running`, `done`, `failed`), `progress` SMALLINT (0-100), `total` INTEGER, `processed` INTEGER
- `error` TEXT, `created_at` TIMESTAMPTZ, `updated_at` TIMESTAMPTZ

**chat_logs** (opsional)
- `id` BIGSERIAL (PK), `owner_channel_id` TEXT, `question` TEXT, `tool_used` TEXT, `answer` TEXT, `created_at` TIMESTAMPTZ

**app_meta**
- `key` TEXT (PK), `value` JSONB; berisi `model_version`, `normalizer_hash`, `sklearn_version`, `loaded_at`, dan penghitung pemakaian kuota harian

### 11.2 Indeks, Aturan, dan Urutan Migrasi

- `comments(owner_channel_id, video_id, zone)`, `comments(author_channel_id)`, `comments(text_hash)`, `keywords(owner_channel_id, video_id)`, `jobs(owner_channel_id, status)`.
- Indeks GIN `pg_trgm` pada `comments.text_original` bila pencarian teks terasa lambat.
- Semua query ke `comments`, `keywords`, `moderation_log`, dan `jobs` wajib memfilter `owner_channel_id` dari sesi login.
- Migrasi skema memakai Alembic (`flask db migrate` dan `flask db upgrade`) dan dibuat bertahap per part:
  - Part 3: `users` dan `app_meta`.
  - Part 4: `videos`, `comments` (kolom klasifikasi dibuat nullable), dan `jobs`.
  - Part 6: `moderation_log`.
  - Part 7: `keywords`.
  - Part 8: `chat_logs` (opsional).

### 11.3 Catatan Supabase

- **Supabase adalah PostgreSQL terkelola**: SQLAlchemy dan Alembic dipakai seperti PostgreSQL biasa, dengan connection string dari dasbor Supabase yang disimpan di environment variable.
- **Jenis koneksi (Ditetapkan: Session Mode Pooler).** Aplikasi menggunakan **Connection Pooler Mode Session** (Supavisor pada port `5432`, host `*.pooler.supabase.com`). Mode Session dipilih karena mendukung jaringan **IPv4** di berbagai layanan hosting PaaS gratis sekaligus mendukung penuh *prepared statements* SQLAlchemy dan eksekusi migrasi Alembic (`flask db upgrade`), berbeda dengan mode transaction yang tidak mendukung prepared statement. Ukuran pool di SQLAlchemy dibatasi kecil (`pool_size=4`, `max_overflow=2`, `pool_pre_ping=True`, `pool_recycle=300`) agar aman di dalam batas koneksi simultan tier gratis Supabase.
- **Row Level Security (RLS).** Tabel di skema `public` dapat terekspos lewat REST API otomatis Supabase. Aktifkan RLS pada semua tabel tanpa policy, sehingga akses lewat kunci publik ditolak, sementara aplikasi Flask tetap mengakses lewat koneksi database server-side.
- **Frontend tidak pernah berbicara ke Supabase.** Kunci `anon` dan `service_role` tidak dipakai di aplikasi dan tidak boleh ada di frontend maupun repositori.
- **Tier gratis.** Perhatikan batas penyimpanan database, jumlah koneksi, dan kemungkinan proyek dijeda bila lama tidak aktif. Aktifkan kembali dan cek koneksi sebelum demo, serta sediakan skrip pembersihan data.
- **Cadangan.** Ekspor data berkala (misalnya `pg_dump`) sebelum demo penting.

---

## 12. Rancangan Endpoint API

Endpoint didefinisikan sebagai Flask Blueprint (`auth`, `videos`, `comments`, `keywords`, `chat`, `tasks`) dengan respons JSON. Endpoint yang mengubah data dilindungi token CSRF (header khusus) selain cookie sesi.

- `GET /auth/login`, `GET /auth/callback`, `POST /auth/logout`
- `GET /api/me`: profil dan status sesi (dipakai React untuk auth guard)
- `GET /api/videos`: daftar video channel (otomatis mengecek retensi 30 hari; bila sudah lewat 30 hari setelah pengguna login kembali, sistem menghapus cache kedaluwarsa, melakukan hit API YouTube lagi, dan menyimpan ulang ke database)
- `POST /api/videos/{video_id}/scan`: **endpoint utama saat klik tombol Scan** — mengambil seluruh komentar video secara *batch* (`maxResults=100`, *bulk upsert*) lalu langsung mengklasifikasikannya sekaligus sebagai **satu array** (membuat job `scan`)
- `POST /api/videos/{video_id}/fetch`: ambil komentar secara terpisah bila diperlukan (membuat job `fetch`)
- `GET /api/videos/{video_id}/comments`: mengambil komentar yang sudah diklasifikasi dengan filter zona, pencarian, dan paginasi sisi server
- `POST /api/videos/{video_id}/classify`: klasifikasi ulang array komentar yang tersimpan (membuat job `classify`)
- `GET /api/tasks/{task_id}`: status dan progres job
- `POST /api/comments/label`: koreksi manual
- `POST /api/comments/reject`: reject terpilih atau semua judol (menggunakan *multi-ID batching* pada `comments.setModerationStatus`)
- `POST /api/videos/{video_id}/keywords/extract` dan `GET /api/videos/{video_id}/keywords`
- `POST /api/chat`
- `GET /health`: status aplikasi, versi model, dan kecocokan hash normalizer

Semua endpoint `/api/*` memerlukan sesi login dan memfilter data berdasarkan pemilik.

---

## 13. YouTube Data API v3: Batasan dan Strategi

Bagian ini mengacu pada dokumentasi resmi YouTube Data API v3 (resource, operasi, kuota, partial response, ETag, dan gzip). Angka kuota dapat berubah, jadi verifikasi ulang di Konsol API dan tabel biaya kuota sebelum menetapkan batas di aplikasi.

### 13.1 Resource dan Operasi yang Dipakai

- `channel`: mengambil ID playlist *uploads* channel pengguna (`channels.list`, `mine=true`).
- `playlistItem`: daftar video dari playlist *uploads* (`playlistItems.list`).
- `video`: detail dan jumlah komentar (`videos.list`).
- `commentThread` dan `comment`: komentar utama dan moderasinya (`commentThreads.list`, `comments.setModerationStatus`).
- Operasi `list` data publik dapat dilakukan tanpa otorisasi, tetapi operasi yang menyisipkan, mengubah, atau menghapus resource (termasuk moderasi) **selalu memerlukan otorisasi pengguna**. Karena aplikasi ini membaca video milik pengguna dan melakukan moderasi, alurnya memakai OAuth.
- **Reject, bukan hapus permanen**: moderasi memakai `comments.setModerationStatus` dengan status `rejected`.

### 13.2 Kuota

- Alokasi default: **10.000 unit per hari** untuk gabungan seluruh endpoint, selain batas terpisah untuk `search.list` dan `videos.insert` (masing-masing 100 panggilan per hari menurut dokumentasi). Kuota tambahan dapat diminta lewat formulir permintaan penambahan kuota.
- **Semua permintaan, termasuk yang tidak valid, dikenai minimal 1 unit.**
- Perkiraan biaya: operasi baca (`list`) sekitar 1 unit per halaman; operasi tulis (`comments.setModerationStatus`) sekitar 50 unit per panggilan HTTP.
- Gambaran beban & penghematan kuota:
  - **Saat klik video**: tidak ada panggilan `commentThreads.list` yang dijalankan otomatis; pengambilan komentar baru dieksekusi ketika pengguna menekan tombol **Scan**.
  - **Saat Scan komentar**: satu video berisi 5.000 komentar diambil secara *batch* (`maxResults=100` per halaman), sehingga hanya membutuhkan sekitar 50 unit kuota baca.
  - **Saat Reject komentar (`comments.setModerationStatus`)**: karena parameter `id` menerima daftar `comment_id` yang dipisahkan koma (multi-ID batching hingga **50 ID per panggilan API**), me-reject 200 komentar judol cukup dikelompokkan menjadi 4 panggilan batch (sekitar 200 unit kuota), menghemat kuota hingga 50x lipat dibandingkan memanggil endpoint satu per satu.

### 13.3 Strategi Hemat Kuota dan Bandwidth

- **Tidak memuat komentar mentah saat pilih video (*on-demand scan*)**: mengklik video di daftar hanya menampilkan metadata video (atau hasil klasifikasi yang sudah ada di cache < 30 hari). Panggilan API pengambilan komentar baru berjalan saat pengguna menekan tombol **Scan**, dan langsung dilanjutkan dengan klasifikasi satu array.
- **Batching pada pengambilan komentar dan reject**: pengambilan komentar memakai halaman maksimum (`maxResults=100`) disertai *bulk upsert* ke database, sedangkan moderasi reject mengelompokkan beberapa `comment_id` sekaligus (comma-separated multi-ID, maks. 50 ID per panggilan) ke `comments.setModerationStatus`.
- **Playlist *uploads*** untuk daftar video (bukan `search.list`).
- **Parameter `part` dan `fields`** pada setiap permintaan, agar hanya properti yang dipakai yang diambil. Contoh untuk komentar: `part=snippet`, dengan `fields` yang membatasi `nextPageToken` dan properti komentar yang diperlukan (ID, teks, nama penulis, `authorChannelId`, waktu, jumlah like).
- **Gunakan `textFormat=plainText`** dan baca `textDisplay`, karena teks asli mentah hanya dijamin tersedia bagi penulis komentar sendiri.
- **Pengambilan inkremental**: untuk video yang pernah diambil dalam masa retensi (< 30 hari), ambil komentar terbaru dulu dan berhenti begitu bertemu komentar yang sudah tersimpan, agar tidak membaca ulang seluruh halaman.
- **ETag** (`If-None-Match`) dan **kompresi gzip** (`Accept-Encoding: gzip` dan `User-Agent` yang memuat `gzip`) mengurangi latensi dan bandwidth. Keduanya **tidak menghemat kuota**, karena setiap permintaan tetap dikenai biaya.
- **Batas maksimum komentar per pengambilan** dan **cache di PostgreSQL** agar data yang sama tidak diambil berulang selama masih dalam masa retensi 30 hari.
- **Penghitung kuota harian** di `app_meta` untuk menampilkan estimasi dan peringatan sebelum reject massal.
- Tangani galat `quotaExceeded`, `commentsDisabled`, dan token kedaluwarsa dengan pesan yang jelas.

### 13.4 Kebijakan dan Lingkungan

- **OAuth mode Testing.** Scope `youtube.force-ssl` bersifat sensitif, sehingga aplikasi yang belum diverifikasi hanya dapat dipakai *test user* (maks. 100). Akun penguji didaftarkan manual.
- **Balasan (reply)** tidak termasuk versi 1.
- **Kebijakan data.** Mematuhi YouTube API Services Developer Policies (penyimpanan dan penghapusan data).
- **Istilah di laporan:** pengambilan data memakai "YouTube Data API v3" (API resmi), bukan scraping.

---

## 14. Kebutuhan Non-Fungsional

### 14.1 Keamanan
- `client_secret`, API key LLM, kunci enkripsi, dan `DATABASE_URL` Supabase hanya di environment variable; `.env` masuk `.gitignore`.
- RLS aktif pada semua tabel di Supabase (tanpa policy); kunci `anon` dan `service_role` tidak dipakai; frontend tidak mengakses Supabase langsung.
- Token OAuth hanya di server dan refresh token dienkripsi (Fernet); cookie sesi `HttpOnly`, `Secure`, `SameSite`. Token tidak disimpan di `localStorage` maupun di cookie sesi bawaan Flask (yang hanya ditandatangani, tidak dienkripsi).
- Isolasi data antar pengguna pada setiap query; query SQL parameterized lewat SQLAlchemy.
- Perlindungan CSRF pada endpoint yang mengubah data; rate limit pada endpoint berat (klasifikasi, ekstraksi, chat) dengan Flask-Limiter; konfigurasi CORS seketat mungkin.
- Frontend merender komentar sebagai teks (tanpa `dangerouslySetInnerHTML`) untuk mencegah XSS.
- Chatbot hanya memiliki tool read-only; tidak ada tool yang dapat me-reject komentar.
- Mitigasi prompt injection (delimiter, validasi output, LLM tanpa tool saat ekstraksi).
- File `.joblib` hanya dimuat dari artefak yang dilatih sendiri.

### 14.2 Privasi dan Retensi Data

Aplikasi menyimpan data pihak ketiga (nama akun dan isi komentar orang lain), sehingga perlu aturan jelas tentang berapa lama data disimpan dan bagaimana pengguna dapat menghapusnya.

- **Minimisasi ke LLM**: hanya teks komentar berlabel judol, tanpa nama akun, yang dikirim ke penyedia LLM.
- **Retensi komentar 30 hari & re-fetch saat login kembali**:
  - Angka retensi final ditetapkan **30 hari** (`last_fetched_at < now() - INTERVAL '30 days'`). Komentar dan hasil analisis yang berusia lebih dari 30 hari dihapus otomatis dari database.
  - Apabila pengguna **login kembali** setelah datanya melewati masa retensi 30 hari, sistem menghapus data lama yang kedaluwarsa, melakukan **hit YouTube Data API v3 kembali**, dan menyimpan ulang data terbaru ke database untuk siklus retensi 30 hari berikutnya.
- **Hapus data atas permintaan pengguna**: tombol "Hapus data saya" menghapus komentar, kata kunci, log, dan token, serta mencabut izin akses di akun Google.
- **Token**: refresh token terenkripsi dan dihapus saat pengguna memutus akun atau menghapus datanya.
- **Tanpa penjualan atau pembagian data** ke pihak lain di luar penyedia LLM dan Supabase.
- Dataset publik dan data pengguna tidak dipublikasikan beserta identitas akun.
- Cantumkan di laporan dan di halaman kebijakan privasi bahwa penyedia LLM tier gratis dapat memiliki kebijakan penggunaan data sendiri.

### 14.3 Konsistensi Model
- Aplikasi **selalu memanggil `prepare()`** sebelum prediksi.
- Hash SHA-256 `normalizer.py` (`4a078a0c99576d727a8c6660334d91d5c9c209800bb21f896a02f8c7e1b8e214` pada artefak Part 0) disimpan di `metrics.json` / `app_meta` dan dibandingkan saat startup; jika berbeda, aplikasi mencatat peringatan dan `/health` melaporkan status tidak cocok.
- `scikit-learn==1.6.1` dikunci di `requirements.txt`.

### 14.4 Performa dan Keandalan
- Model dimuat sekali saat startup; saat klasifikasi, seluruh komentar yang belum diklasifikasi dikumpulkan menjadi **satu array** dan diprediksi sekaligus (`model.predict_proba(array)`).
- Proses Scan (pengambilan komentar batch + klasifikasi array) dan ekstraksi kata kunci berjalan sebagai background task dengan progres.
- Retry dengan backoff untuk YouTube API dan LLM; penanganan `quotaExceeded`, `commentsDisabled`, token kedaluwarsa, dan JSON LLM rusak.
- Fitur inti (klasifikasi, review, reject) tidak bergantung pada LLM.

### 14.5 Usability
- Antarmuka berbahasa Indonesia, responsif.
- Konfirmasi eksplisit sebelum reject dengan jumlah dan estimasi kuota.
- Indikator progres untuk proses panjang.

---

## 15. Rencana Pengerjaan Bertahap

Setiap part menghasilkan sesuatu yang dapat didemokan dan ditandai sebagai rilis (`v0.1`, `v0.2`, dan seterusnya) di GitHub, sehingga kemajuan terlihat jelas.

### Papan Progres

| Part | Nama | Rilis | Status |
| --- | --- | --- | --- |
| 0 | Fondasi data dan model ML | v0.0 | ✅ Selesai |
| 1 | Fondasi aplikasi | v0.1 | ✅ Selesai |
| 2 | Implementasi OAuth login | v0.2 | ✅ Selesai (Backend) |
| 3 | Database Supabase | v0.3 | ✅ Selesai |
| 4 | Pengambilan video dan komentar | v0.4 | ⬜ Belum |
| 5 | Klasifikasi dan review | v0.5 | ⬜ Belum |
| 6 | Reject komentar | v0.6 | ⬜ Belum |
| 7 | Ekstraksi kata kunci | v0.7 | ⬜ Belum |
| 8 | Chatbot analisis spam | v0.8 | ⬜ Belum |
| 9 | Perbaikan | v0.9 | ⬜ Belum |
| 10 | Deploy dan finalisasi | v1.0 | ⬜ Belum |

Cara menjaga progres tetap terlihat: satu *milestone* GitHub per part, commit yang bermakna, berkas `CHANGELOG.md`, tangkapan layar atau rekaman demo singkat di tiap rilis, dan pembaruan papan progres ini setiap part selesai.

---

### Part 0: Fondasi Data dan Model ML (✅ Selesai)

**Tujuan:** memiliki model klasifikasi yang teruji dan siap diintegrasikan.

**Hasil:**
- [x] Dataset dikumpulkan, dibersihkan, dan dideduplikasi (32.626 komentar).
- [x] `normalizer.py` dengan `normalize()` dan `prepare()` (masking brand).
- [x] Pengelompokan kalimat mirip dan split per kelompok untuk mencegah kebocoran data.
- [x] Model TF-IDF + LinearSVC terkalibrasi, ukuran ± 2,9 MB.
- [x] Evaluasi: test, leave-brand-out, ablasi masking, dan uji eksternal (live chat Jogja).
- [x] `metrics.json` berisi threshold dan seluruh metrik.

**Catatan yang dibawa ke part berikutnya:** batasan model di bagian 9.5 dan daftar perbaikan di Part 9.

---

### Part 1: Fondasi Aplikasi (v0.1)

**Tujuan:** kerangka backend Flask dan frontend React TypeScript berjalan dan saling terhubung.

**Pekerjaan:**
- Repositori GitHub dengan struktur pada 8.6, `.gitignore`, `.env.example`, `README` awal, `CHANGELOG.md`, dan aturan commit/branch.
- **Backend**: virtualenv, `requirements.txt` (dengan `scikit-learn==1.6.1`), application factory, konfigurasi dari environment, penanganan error JSON seragam, logging, Blueprint kosong per modul, dan endpoint `/health`.
- **Frontend**: scaffold Vite + React + TypeScript, Tailwind CSS, React Router, layout dasar, klien API bertipe, TanStack Query, dan proxy pengembangan Vite ke Flask.
- Perkakas pengembangan: linter dan formatter (ESLint, Prettier, Ruff atau Black) serta skrip untuk menjalankan backend dan frontend.

**Kriteria selesai:**
- Backend dan frontend berjalan lokal dengan satu perintah masing-masing.
- Halaman beranda menampilkan status dari `/health`.
- Repositori bersih dari secret dan `README` menjelaskan cara menjalankan.

**Demo:** halaman beranda menampilkan status "backend terhubung".

**Risiko:** perbedaan versi Python atau Node (mitigasi: dokumentasikan versi di `README`).

---

### Part 2: Implementasi OAuth Login (v0.2)

**Tujuan:** pengguna dapat login dengan akun Google dan mengizinkan akses ke channel YouTube-nya.

**Pekerjaan:**
- **Google Cloud**: buat project, aktifkan YouTube Data API v3, atur OAuth consent screen (mode Testing), daftarkan test user (termasuk dosen/penguji), dan buat Client ID dengan redirect URI lokal.
- **Authlib**: endpoint `/auth/login`, `/auth/callback`, dan `/auth/logout`; scope `youtube.force-ssl`; validasi parameter `state`; ambil `channel_id` lewat `channels.list` (`mine=true`).
- **Sesi**: cookie `HttpOnly` dan `SameSite`. Token OAuth **tidak disimpan di cookie sesi bawaan Flask**. Sampai Part 3, token disimpan sementara di penyimpanan sesi sisi server (misalnya Flask-Session), lalu dipindahkan ke database terenkripsi di Part 3.
- Endpoint `/api/me`.
- **Frontend**: halaman Login, auth guard, tombol logout, dan penanganan sesi kedaluwarsa.

**Kriteria selesai:**
- Test user dapat login dan logout.
- Rute yang dilindungi mengarahkan pengguna yang belum login ke halaman Login.
- Tidak ada token di `localStorage` maupun cookie sisi klien.

**Demo:** login dengan akun test user, lalu beranda menampilkan nama dan channel.

**Risiko:** verifikasi OAuth (mitigasi: mode Testing dan test user), salah redirect URI, dan cookie yang tidak terkirim bila frontend dan backend berbeda origin (mitigasi: proxy pengembangan Vite).

---

### Part 3: Database Supabase (v0.3)

**Tujuan:** data pengguna tersimpan di PostgreSQL Supabase melalui lapisan query yang aman.

**Pekerjaan:**
- Buat proyek Supabase, gunakan connection string **Session Mode Pooler** (port `5432` pada host pooler; lihat 11.3), dan simpan di environment variable.
- Konfigurasi Flask-SQLAlchemy (`pool_size=4`, `max_overflow=2`, `pool_pre_ping=True`, `pool_recycle=300`) dan Flask-Migrate yang berjalan terhadap Supabase.
- Model dan migrasi `users` dan `app_meta`.
- Aktifkan RLS pada semua tabel (tanpa policy).
- Lapisan query (`repositories/`): upsert pengguna saat login, ambil pengguna, serta simpan dan baca refresh token terenkripsi (Fernet), dengan filter pemilik pada setiap query.
- Pindahkan penyimpanan token dari sesi sementara (Part 2) ke database terenkripsi.
- Tambahkan status koneksi database ke `/health`.
- Uji repository dengan database uji terpisah (proyek atau skema Supabase khusus pengujian).

**Kriteria selesai:**
- Login membuat atau memperbarui baris di tabel `users`.
- Refresh token di database tersimpan terenkripsi (bukan teks biasa).
- `flask db upgrade` berjalan dari database kosong lewat koneksi Session Mode Pooler.
- RLS aktif pada semua tabel dan tidak ada secret atau connection string di repositori.

**Demo:** login, lalu tunjukkan baris pengguna di Table Editor Supabase.

**Risiko:** batas koneksi simultan tier gratis pada Session Mode Pooler dan proyek tier gratis yang dijeda saat lama tidak aktif (mitigasi: ukuran pool kecil dan lihat 11.3).

---

### Part 4: Pengambilan Video dan Komentar secara Batch (v0.4)

**Tujuan:** daftar video channel pengguna terambil, dan komentar video dapat diambil secara *batch* saat tombol Scan ditekan (tanpa memuat komentar otomatis saat baru mengklik video).

**Pekerjaan:**
- **Layanan YouTube** (`services/youtube.py`): daftar video dari playlist *uploads*, `videos.list` untuk detail, pengambilan komentar secara *batch* (`maxResults=100` per halaman), `part`/`fields`, gzip, batas maksimum, penanganan error (`commentsDisabled`, `quotaExceeded`), pengambilan inkremental untuk video yang pernah diambil, serta pengecekan retensi 30 hari saat pengguna login/membuka daftar video.
- Migrasi `videos`, `comments` (kolom klasifikasi nullable), dan `jobs`.
- *Bulk upsert* komentar dengan `ON CONFLICT (comment_id) DO UPDATE` serta sistem job (`ThreadPoolExecutor`, pembaruan progres, endpoint `/api/tasks/{id}`).
- **Frontend**: halaman daftar video dan halaman detail video. Saat pengguna mengklik video, halaman **tidak** langsung memanggil API komentar (hanya menampilkan info video dan tombol Scan, atau hasil yang sudah tersimpan di database bila berusia < 30 hari).

**Kriteria selesai:**
- Daftar video tampil dengan judul, thumbnail, dan jumlah komentar.
- Mengklik video tidak menguras kuota `commentThreads.list` sebelum pengguna menekan tombol Scan.
- Komentar satu video (≥ 1.000 komentar) terambil secara *batch* tanpa duplikasi (*bulk upsert*), dan job yang terputus dapat dijalankan ulang tanpa data ganda.
- Pemakaian kuota tercatat dan ditampilkan.

**Demo:** pilih video (tunjukkan belum ada komentar mentah yang dimuat otomatis), jalankan pengambilan batch, dan lihat progresnya.

**Risiko:** kuota API pada video besar (mitigasi: on-demand scan, batas maksimum, dan pengambilan inkremental) dan job terputus karena restart (mitigasi: job idempoten).

---

### Part 5: Klasifikasi Satu Array dan Review (v0.5)

**Tujuan:** saat pengguna menekan tombol **Scan**, seluruh komentar yang diambil langsung diklasifikasikan sekaligus sebagai **satu array** ke tiga zona dan ditampilkan untuk ditinjau serta dikoreksi pengguna.

**Pekerjaan:**
- **Layanan klasifikasi**: muat model sekali saat startup, kumpulkan seluruh komentar yang belum diklasifikasi menjadi **satu array**, jalankan `[prepare(t) for t in array]`, deduplikasi berdasarkan `text_hash`, panggil `model.predict_proba(unique_array)` **satu kali untuk keseluruhan array**, dan terapkan `t_low` dan `t_high` dari `metrics.json`.
- **Lapisan aturan** (`rules.py`) yang menaikkan "bukan" menjadi "perlu review".
- **Pengecekan hash normalizer** saat startup, disimpan di `app_meta` dan dilaporkan di `/health`.
- Integrasi alur **Scan** (`POST /api/videos/{video_id}/scan`): menggabungkan *batch fetch* (Part 4) dan *array classification* (Part 5) dalam satu alur job dengan progres dan *bulk update* hasil (zona, skor, penanda aturan, versi model, waktu).
- **Frontend**: tombol **"Scan & Klasifikasi"**, tabel hasil yang baru muncul setelah komentar selesai diklasifikasi dengan filter tiga zona, pengurutan skor, tampilan skor dan penanda aturan per komentar, serta tombol koreksi label ("bukan judol" / "judol") yang disimpan sebagai `user_label`.

**Kriteria selesai:**
- Waktu klasifikasi 1.000 komentar sebagai satu array kurang dari 10 detik (target aktual < 1 detik di memori).
- Uji kesetaraan: komentar contoh menghasilkan skor yang sama dengan notebook (versi model dan hash normalizer sama).
- Mengubah `normalizer.py` memicu peringatan di `/health`.
- Koreksi label tersimpan dan tampil setelah halaman dimuat ulang.

**Demo:** klik video, tekan "Scan & Klasifikasi", tunggu progres selesai, tunjukkan keseluruhan komentar yang langsung tampil dalam tiga zona beserta skornya, lalu koreksi satu label.

**Risiko:** perbedaan hasil model antara notebook dan aplikasi (mitigasi: uji kesetaraan dan pengecekan hash) dan job terputus (mitigasi: job idempoten).

---

### Part 6: Reject Komentar (v0.6)

**Tujuan:** pengguna dapat me-reject komentar judol dengan aman dan hemat kuota.

**Pekerjaan:**
- **Implementasi Multi-ID Batch Reject**: gunakan parameter `id` berisi kumpulan `comment_id` yang dipisahkan koma (hingga 50 ID per panggilan) pada `comments.setModerationStatus(id="id1,id2,...", moderationStatus="rejected")` untuk menghemat kuota API secara maksimal, dan verifikasi pencatatan kuotanya.
- Migrasi `moderation_log`.
- Endpoint reject (satu per satu, terpilih, semua judol), pemrosesan per batch multi-ID, dan penanganan kegagalan bila ada batch/komentar yang gagal.
- Penghitung kuota harian di `app_meta`.
- **Frontend**: pemilihan baris (checkbox, pilih semua di halaman, pilih semua judol), dialog konfirmasi berisi jumlah komentar dan estimasi kuota (dihitung per batch multi-ID), serta penanda status moderasi pada tabel.

**Kriteria selesai:**
- Komentar yang di-reject benar-benar tidak tampil publik di YouTube.
- Tidak ada reject tanpa aksi dan konfirmasi pengguna.
- Kegagalan sebagian (misalnya kuota habis) dilaporkan jelas tanpa merusak data.

**Demo:** reject beberapa komentar judol sekaligus secara batch dan tunjukkan hasilnya di YouTube.

**Risiko:** kuota `setModerationStatus` yang mahal bila dipanggil satu-satu (mitigasi: pengelompokan multi-ID hingga 50 ID per request, estimasi di UI, dan batas per sesi).

---

### Part 7: Ekstraksi Kata Kunci (v0.7)

**Tujuan:** pengguna mendapat daftar kata kunci siap salin untuk *Blocked words* YouTube Studio.

**Pekerjaan:**
- Migrasi `keywords`.
- Layanan ekstraksi (`services/extractor.py`): adapter LLM (Gemini utama, Groq cadangan; lihat 10.3) dengan output JSON terstruktur, temperature 0, batching, dedup komentar sebelum dikirim, dan tanpa nama akun.
- Validasi: struktur JSON, ID, dan substring kata di teks asli; retry dengan backoff.
- Agregasi frekuensi, penyaringan kata umum, dan penyimpanan hasil sebagai cache; dijalankan sebagai job.
- **Frontend**: halaman kata kunci dengan checkbox, jumlah kemunculan, dan tombol **Copy** (Clipboard API) berformat dipisah koma.

**Kriteria selesai:**
- 100% kata kunci yang ditampilkan ada di teks asli komentar sumber.
- Daftar dapat ditempel ke YouTube Studio dan diterima.
- Aplikasi tetap berfungsi (tanpa kata kunci) bila LLM tidak tersedia.

**Demo:** ekstraksi dari satu video, pilih kata, salin, dan tempel ke YouTube Studio.

**Risiko:** rate limit tier gratis, JSON rusak, dan prompt injection dari isi komentar (mitigasi: batching, validasi ketat, delimiter).

---

### Part 8: Chatbot Analisis Spam (v0.8)

**Tujuan:** pengguna dapat bertanya tentang akun dan pola spam dan mendapat jawaban berbasis data.

**Pekerjaan:**
- Blueprint `chat`, definisi tool dan registry fungsi (7 tool pada 10.2); semua query read-only, parameterized, dan difilter pemilik data.
- Intent routing oleh LLM lewat tool calling, jawaban disusun dari template.
- Adapter LLM dengan rantai Gemini, Groq, lalu pesan statis "analisis AI tidak tersedia" (10.3); tombol pertanyaan siap pakai tetap berfungsi tanpa LLM.
- Fallback untuk pertanyaan di luar cakupan dan penanganan data kosong; rate limit pada `/api/chat`.
- **Frontend**: antarmuka chat dengan riwayat percakapan, chip pertanyaan siap pakai, dan indikator memuat; opsional migrasi `chat_logs`.

**Kriteria selesai:**
- Minimal 7 jenis pertanyaan dijawab dengan benar dari database.
- Akurasi pemilihan tool ≥ 85% pada 30 pertanyaan uji (campuran dalam cakupan, data kosong, di luar cakupan, variasi bahasa).
- Chatbot tidak pernah menampilkan data milik pengguna lain.

**Demo:** tanyakan "akun mana yang paling sering spam?" dan "situs apa yang paling banyak muncul?".

**Risiko:** LLM tidak memanggil tool padahal seharusnya (mitigasi: deskripsi tool jelas, aturan "wajib pakai tool", temperature 0, uji 30 pertanyaan).

---

### Part 9: Perbaikan (v0.9)

**Tujuan:** menutup batasan model yang diketahui, merapikan aplikasi, dan membuktikan kualitas lewat pengujian. Aplikasi web tidak memiliki halaman evaluasi; seluruh hasil evaluasi didokumentasikan di laporan dan notebook.

**Pekerjaan:**
- **Perbaiki masking brand**: gunakan leksikon brand dari data latih dan isyarat judol lain untuk token tak dikenal, sehingga `iphone15`, `yamaha125`, `covid19`, `darwin`, dan `film 4d` tidak lagi tersamarkan. Latih ulang, perbarui `metrics.json`, dan perbarui salinan `normalizer.py` di backend (hash baru).
- **Uji *hard negative***: 50-100 komentar normal berisi nama produk, tahun, dan game; target nol salah label.
- **Uji data nyata YouTube**: kumpulkan komentar dari video yang tidak ada di data latih lewat API, sampling acak ditambah kandidat spam, labeli manual tanpa melihat skor model (idealnya dua pelabel pada sebagian sampel untuk mengukur kesepakatan). Evaluasi terpisah untuk sampel acak.
- Periksa ulang tabel perbandingan penyeimbangan data (tiga metode menghasilkan angka identik, perlu diverifikasi) dan perluas grid `C` (nilai 10 dan 20).
- Perbaikan UX: pesan error, keadaan kosong dan memuat, serta penanganan kuota habis dan LLM tidak tersedia.
- **Kebijakan retensi data (30 hari) & re-fetch saat login kembali**: tombol "Hapus data saya" (menghapus komentar, kata kunci, log, dan token, serta mencabut izin di Google), pembersihan otomatis untuk komentar yang berusia lebih dari 30 hari, serta mekanisme pengecekan saat pengguna login kembali untuk melakukan hit API ulang dan menyimpan ke database apabila data sebelumnya telah melewati batas retensi 30 hari (lihat 14.2).
- Uji backend (pytest) dan frontend (Vitest dan React Testing Library), lalu perbaiki temuan (lihat bagian 16).

**Kriteria selesai:**
- Hasil uji hard negative dan data nyata terdokumentasi di laporan dengan hitungan mentah dan rentang kepercayaan.
- Seluruh uji otomatis lulus.
- Tidak ada galat `tsc` dan tidak ada temuan keamanan terbuka dari daftar uji dasar.

**Demo:** tunjukkan perbandingan sebelum dan sesudah perbaikan masking (di notebook atau laporan) dan aplikasi yang berjalan dengan model terbaru.

---

### Part 10: Deploy dan Finalisasi (v1.0)

**Tujuan:** aplikasi dapat diakses penguji dan terdokumentasi lengkap.

**Pekerjaan:**
- Build frontend (`npm run build`) dan sajikan lewat Flask dari `frontend/dist` (origin yang sama dengan backend).
- Deploy backend dengan Gunicorn ke hosting gratis; hubungkan ke Supabase memakai **Session Mode Pooler** (lihat 11.3); jalankan `flask db upgrade` terhadap Supabase; atur redirect URI OAuth produksi dan environment variable.
- Daftarkan akun dosen/penguji sebagai test user.
- Penyempurnaan UI, pesan error, dan kebijakan privasi/retensi data.
- `README` (cara menjalankan, setup OAuth, variabel lingkungan, migrasi), `CHANGELOG.md`, dan skrip demo.
- Laporan: latar belakang, metode, hasil evaluasi, batasan, dan refleksi.

**Kriteria selesai:**
- Seluruh kriteria penerimaan (bagian 17) terpenuhi.
- Penguji dapat login dan menjalankan alur lengkap tanpa bantuan.

---

## 16. Rencana Pengujian

- **Uji unit backend (pytest)**: `prepare()` (kasus pengaburan teks dan hard negative), validasi substring kata kunci, template jawaban chatbot, aturan, dan filter kepemilikan data.
- **Uji API (Flask test client)** dengan database PostgreSQL uji agar perilaku `ON CONFLICT` dan constraint sama dengan produksi.
- **Uji kesetaraan model**: komentar contoh di aplikasi menghasilkan skor yang sama dengan notebook (versi model dan hash normalizer sama).
- **Uji model**: data uji, leave-brand-out, uji eksternal, hard negative, dan komentar nyata YouTube.
- **Uji integrasi**: alur OAuth, pengambilan komentar, klasifikasi, dan reject (dengan akun test user).
- **Uji frontend (Vitest dan React Testing Library)**: komponen tabel hasil, dialog konfirmasi reject, daftar kata kunci dan tombol Copy, serta antarmuka chat; pengecekan tipe `tsc` tanpa galat.
- **Uji uji-ujung (opsional, Playwright)**: alur login sampai kata kunci dengan data tiruan.
- **Uji LLM**: validitas JSON dan kata kunci pada 20-50 komentar judol; kasus injeksi prompt (komentar berisi instruksi).
- **Uji chatbot**: 30 pertanyaan; catat akurasi pemilihan tool.
- **Uji keamanan dasar**: akses data pengguna lain, parameter tool tidak valid, CSRF, XSS pada isi komentar, dan tidak ada secret di repositori.
- **Uji kuota dan job**: skenario reject banyak komentar, kuota habis, dan job yang terputus lalu dijalankan ulang.

---

## 17. Kriteria Penerimaan Akhir

1. Test user dapat login dan melihat daftar video channel-nya.
2. Data pengguna tersimpan di Supabase dan refresh token tersimpan terenkripsi.
3. Komentar video tidak dimuat otomatis saat video diklik; saat tombol Scan ditekan, komentar diambil secara *batch* (`maxResults=100`), tersimpan tanpa duplikasi (*bulk upsert*), dan langsung diklasifikasikan sekaligus sebagai satu array.
4. Klasifikasi menghasilkan zona dan skor untuk seluruh komentar yang diambil dalam satu array panggilan model, dengan masukan model selalu dari `prepare()`.
5. Pengguna dapat me-reject komentar satuan, terpilih, dan semua judol (dengan pengelompokan *multi-ID batch* pada `comments.setModerationStatus`); status tercermin di YouTube dan database.
6. Tidak ada komentar yang di-reject tanpa aksi dan konfirmasi pengguna.
7. Kata kunci tampil dengan checkbox dan tombol Copy; seluruhnya ada di teks asli komentar.
8. Chatbot menjawab minimal 7 jenis pertanyaan berbasis data dan memberi fallback yang jelas untuk pertanyaan di luar cakupan.
9. Chatbot tidak pernah menampilkan data milik pengguna lain.
10. Aplikasi (Flask, React TypeScript, dan PostgreSQL di Supabase dengan Session Mode Pooler) berjalan di hosting gratis dan model tersimpan di repositori GitHub.
11. Tidak ada secret di repositori, dan RLS aktif pada semua tabel di Supabase.
12. Pengguna dapat menghapus seluruh datanya dari aplikasi (komentar, kata kunci, log, dan token); data yang melewati retensi 30 hari dibersihkan otomatis, dan saat pengguna login kembali setelah 30 hari sistem melakukan hit API ulang serta menyimpan data baru ke database.

---

## 18. Risiko dan Mitigasi

- **Kuota YouTube API habis** (terutama pengambilan komentar dan reject massal): tidak mengambil komentar saat baru klik video (hanya saat klik Scan), batch fetching (`maxResults=100`), pengelompokan multi-ID hingga 50 ID per panggilan `comments.setModerationStatus`, estimasi di UI, dan penghitung kuota harian.
- **Salah reject komentar asli**: threshold berbasis precision, zona review, konfirmasi, koreksi label, log moderasi.
- **Model turun performa pada jenis spam baru**: lapisan aturan, uji data nyata, kumpulkan koreksi pengguna untuk pelatihan ulang offline.
- **Masking brand salah sasaran**: perbaikan di Part 9 dan uji hard negative.
- **Hasil model di aplikasi berbeda dari notebook**: `prepare()` wajib, pengecekan hash normalizer, versi scikit-learn dikunci, uji kesetaraan.
- **Job latar belakang terputus saat restart atau proses ditidurkan** (Flask tanpa antrean bawaan): tabel `jobs`, job idempoten, pemulihan saat startup, dan opsi RQ/Celery bila diperlukan.
- **Koneksi Supabase bermasalah** (IPv6 pada koneksi langsung, prepared statement di pooler mode transaction): memakai **Session Mode Pooler** (port `5432`) dengan ukuran pool kecil (`pool_size=4`) dan diuji sejak Part 3.
- **Batas tier gratis Supabase dan hosting** (penyimpanan, koneksi, proyek dijeda saat tidak aktif): pantau pemakaian, batasi jumlah komentar tersimpan, jalankan retensi 30 hari, dan cek koneksi sebelum demo.
- **Data terekspos lewat REST API Supabase**: aktifkan RLS tanpa policy pada semua tabel dan jangan pakai kunci `anon` atau `service_role` di aplikasi.
- **Cookie sesi tidak terkirim bila frontend dan backend berbeda origin**: sajikan dari origin yang sama atau atur CORS, `SameSite=None; Secure`, dan CSRF dengan benar.
- **XSS dari isi komentar**: render sebagai teks, tanpa `dangerouslySetInnerHTML`.
- **Rate limit atau gangguan LLM**: batching, cache, dedup, rantai cadangan Gemini, Groq, lalu pesan statis; fitur inti tidak bergantung LLM.
- **Output LLM tidak valid atau berhalusinasi**: structured output, validasi substring, retry.
- **Prompt injection lewat komentar**: delimiter, validasi, LLM tanpa tool saat ekstraksi, chatbot read-only.
- **OAuth belum terverifikasi**: mode Testing dan daftar test user, dijelaskan di laporan.
- **Privasi data pihak ketiga**: minimisasi data ke LLM, kebijakan retensi 30 hari dengan re-fetch saat login ulang, tanpa publikasi dataset berisi identitas.
- **Jadwal terlambat**: pembagian part memungkinkan memotong Part 8 menjadi 4-5 tool dasar dan menunda perbaikan lanjutan di Part 9 tanpa merusak fitur inti.

---

## 19. Keputusan dan Pertanyaan Terbuka

### 19.1 Keputusan yang Sudah Diambil

- UI frontend memakai **Tailwind CSS**.
- Penyedia LLM: **Gemini** sebagai utama, **Groq** sebagai cadangan, lalu pesan "analisis AI tidak tersedia" (10.3).
- **Docker tidak dipakai** (database di Supabase, backend langsung di virtualenv).
- Koneksi database Supabase memakai **Connection Pooler Mode Session** (port `5432`), sehingga kompatibel dengan IPv4 di hosting PaaS sekaligus mendukung *prepared statements* SQLAlchemy dan migrasi Alembic (11.3).
- **Retensi data ditetapkan 30 hari**: komentar dan hasil analisis yang berusia > 30 hari dihapus otomatis; apabila pengguna login kembali setelah melewati 30 hari, sistem melakukan hit YouTube API lagi dan menyimpan ulang ke database (14.2).
- **Alur hemat kuota & klasifikasi satu array**: saat pengguna mengklik video, komentar **tidak** langsung dimuat/ditampilkan; saat pengguna menekan tombol **Scan**, sistem mengambil komentar secara *batch* (`maxResults=100`, *bulk upsert*) lalu langsung memanggil klasifikasi model terhadap keseluruhan komentar sekaligus dalam **satu array** (`model.predict_proba(array)`), sehingga hasil yang tampil di layar langsung berupa komentar yang sudah terklasifikasi (8.2, 13.3).
- **Efisiensi kuota reject (`comments.setModerationStatus`)**: menggunakan **multi-ID batching** (mengirimkan beberapa `comment_id` dipisahkan koma hingga 50 ID dalam satu panggilan API) untuk menekan konsumsi kuota (13.2).
- Frontend React dibuild dan **disajikan dari Flask** (satu deployment, satu origin); dapat diubah bila hosting yang dipilih mengharuskan pemisahan.
- Penggunaan LLM eksternal **diizinkan** oleh dosen.
- Analisis balasan (reply) komentar **ditunda** ke pengembangan lanjutan.
- Jadwal dan tenggat tiap part **tidak dicantumkan** di dokumen ini.

### 19.2 Pertanyaan yang Masih Terbuka

- **Sumber dan lisensi tiap dataset**, akan dilengkapi penyusun pada Lampiran A saat penulisan laporan akhir.

---

## Lampiran A: Sumber Data _(diisi)_

- Dataset latih: _(sumber, tanggal pengambilan, lisensi)_
- Dataset uji eksternal (live chat Jogja): _(sumber, lisensi)_
- Data uji komentar nyata: _(video, tanggal pengambilan, cara pelabelan)_

## Lampiran B: Glosarium

- **Judol**: judi online.
- **Reject**: status moderasi YouTube yang menolak komentar sehingga tidak tampil publik.
- **Blocked words**: fitur YouTube Studio untuk memblokir komentar berisi kata tertentu.
- **TF-IDF**: pembobotan fitur teks berdasarkan frekuensi kata dan kelangkaannya.
- **SVM terkalibrasi**: SVM yang skor keluarannya dikonversi menjadi probabilitas.
- **`prepare()`**: fungsi pintu masuk teks ke model (normalisasi + masking brand).
- **Leave-brand-out**: evaluasi yang menyembunyikan satu kelompok brand dari data latih untuk menguji kemampuan mengenali brand baru.
- **Hard negative**: komentar normal yang mirip judol (misalnya menyebut nama produk atau mengeluh soal spam) dan rawan salah label.
- **Tool calling**: mekanisme LLM memilih fungsi dan parameter yang dieksekusi oleh backend.
- **Test user**: akun yang didaftarkan agar dapat memakai aplikasi OAuth yang belum diverifikasi Google.
- **Application factory**: pola Flask yang membuat aplikasi lewat fungsi, sehingga konfigurasi dan ekstensi mudah diuji.
- **Blueprint**: cara Flask mengelompokkan endpoint per modul.
- **Alembic**: perkakas migrasi skema database untuk SQLAlchemy.
- **Partial response (`part` dan `fields`)**: parameter YouTube Data API untuk mengambil hanya properti yang dibutuhkan.
- **ETag**: penanda versi resource HTTP untuk pengambilan bersyarat; mengurangi bandwidth, bukan kuota.
- **Supabase**: layanan PostgreSQL terkelola; dalam proyek ini hanya dipakai sebagai database.
- **Connection pooler**: perantara koneksi database; mode session cocok untuk server yang berjalan terus, mode transaction untuk serverless.
- **RLS (Row Level Security)**: fitur PostgreSQL untuk membatasi akses baris; diaktifkan tanpa policy agar akses lewat kunci publik ditolak.

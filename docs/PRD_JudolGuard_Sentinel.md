# PRD Tambahan: JudolGuard Sentinel (Pemantauan Komentar Judol via Telegram)

## 1. Ringkasan

JudolGuard versi web baru bekerja ketika pengguna membuka aplikasi dan memeriksa komentar secara manual. Fitur tambahan ini menambahkan **bot Telegram dan scheduler** yang memantau video channel pengguna secara berkala, mengklasifikasikan komentar baru dengan SVM, dan memberi notifikasi ke Telegram ketika ada komentar judol. Tindakan moderasi (review, reject) tetap dilakukan di web.

## 2. Tujuan dan Non-Tujuan

### Tujuan

- Pengguna mengetahui adanya komentar judol baru tanpa membuka web (notifikasi mendekati real-time, dengan jeda sesuai interval polling).
- Pairing akun Telegram dilakukan dengan aman dan sederhana.
- Penggunaan kuota YouTube API ditekan dan terkendali.
- Pengguna dapat melihat status dan ringkasan pemantauan lewat command.

### Non-Tujuan (di luar cakupan fitur ini)

- Reject, ekstraksi kata kunci, chatbot analisis, dan evaluasi model tetap di web.
- Penghapusan atau reject otomatis tanpa keputusan pengguna.
- Pemantauan multi-channel per pengguna dan notifikasi grup Telegram.
- Retraining model otomatis.

## 3. Pengguna dan User Story

- Sebagai pemilik channel, saya ingin dinotifikasi ketika ada komentar judol baru agar bisa meninjau sebelum komentar itu menumpuk.
- Sebagai pemilik channel, saya ingin menghubungkan Telegram dengan mudah tanpa membagikan akses Google saya ke bot.
- Sebagai pemilik channel, saya ingin menjeda atau memutus notifikasi kapan saja.
- Sebagai pemilik channel, saya ingin melihat ringkasan jumlah komentar judol dan akun yang paling sering berkomentar spam dari Telegram.

## 4. Ruang Lingkup Fitur

| Area | Termasuk |
|---|---|
| Pairing | Token sekali pakai dari web, aktivasi lewat `/start <token>` |
| Patroli | Scheduler, pengecekan `commentCount`, pengambilan komentar baru |
| Klasifikasi | SVM pada komentar baru, penyimpanan label dan skor |
| Notifikasi | Pesan ringkasan, tombol tautan ke web, anti-duplikasi |
| Command | `/start`, `/status`, `/stats`, `/topspammer`, `/pause`, `/resume`, `/putuskan`, `/bantuan` |
| Pengendalian | Penanganan `invalid_grant`, kuota habis, batas laju |

## 5. Kebutuhan Fungsional

### FR-1 Pairing

- Web menyediakan tombol "Hubungkan Telegram" yang membuat token sekali pakai (berlaku sekitar 10 menit) dan menampilkan tautan `t.me/<bot>?start=<token>`.
- Saat bot menerima `/start <token>`, sistem memvalidasi token (ada, belum kedaluwarsa, belum dipakai), menyimpan pasangan `chat_id` dan `user_id`, lalu menandai token terpakai. Seluruh proses ini dikerjakan sistem; pengguna hanya menekan tombol di web dan menekan Start di bot.
- `/start` tanpa token menampilkan petunjuk menghubungkan akun lewat web.
- Satu akun pengguna terhubung ke satu `chat_id` aktif.

### FR-2 Sesi dan token Google

- Refresh token tersimpan terenkripsi. Access token diperoleh setiap siklus patroli.
- Jika terjadi `invalid_grant`, patroli pengguna dihentikan dan bot mengirim pesan agar login ulang lewat tautan web.

### FR-3 Patroli terjadwal

- Scheduler menjalankan siklus pada interval tetap untuk setiap pengguna aktif (terhubung, tidak dijeda, sesi valid).
- Per siklus: ambil daftar video terbaru (misalnya 5), panggil `videos.list` (`part=statistics`) sekali untuk semua video, lalu bandingkan `commentCount` dengan nilai tersimpan.
- Hanya video yang `commentCount`-nya **berbeda** dari nilai tersimpan yang diambil komentarnya lewat `commentThreads.list` urut terbaru, berhenti begitu bertemu `comment_id` yang sudah ada di database.
- Siklus pertama sebuah video hanya menyimpan baseline `commentCount`, tanpa mengambil komentar lama.
- Video yang komentarnya dinonaktifkan dilewati.

### FR-4 Klasifikasi komentar baru

- Komentar baru dinormalisasi lalu diklasifikasikan dengan SVM (label dan skor kepercayaan). Teks asli disimpan utuh, hasil disimpan ke database.
- Komentar dikelompokkan: judol, perlu review (zona abu-abu), normal.

### FR-5 Notifikasi

- Notifikasi dikirim hanya jika ada komentar berlabel judol atau perlu review yang belum dinotifikasi.
- Satu siklus menghasilkan **satu pesan ringkasan per video** (jumlah judol dan perlu review, beberapa contoh komentar singkat), dengan tombol tautan **[Tinjau di web]** menuju halaman review video tersebut.
- Setiap komentar ditandai `notified` agar tidak dikirim ulang.
- Ambang notifikasi dapat diatur (opsional): hanya kirim jika jumlah komentar judol minimal N.

### FR-6 Command pemantauan

| Command | Perilaku |
|---|---|
| `/start` | Pairing akun (dengan token), atau petunjuk jika tanpa token |
| `/status` | Status patroli (aktif atau jeda), waktu pemeriksaan terakhir, jumlah komentar judol hari ini |
| `/stats` | Ringkasan per video (judol, perlu review, normal) |
| `/topspammer` | Akun dengan komentar judol terbanyak (query database, tanpa LLM) |
| `/pause` dan `/resume` | Menghentikan atau melanjutkan patroli dan notifikasi tanpa memutus pairing |
| `/putuskan` | Menghapus pasangan `chat_id` dan `user_id` |
| `/bantuan` | Daftar command |

Semua command hanya mengakses data milik `user_id` yang terhubung ke `chat_id` pengirim.

### FR-7 Pengendalian kuota

- Estimasi unit API per siklus dicatat. Jika terjadi error `quotaExceeded`, patroli dijeda sampai kuota direset (tengah malam Pacific Time).
- Batas laju pengiriman pesan per pengguna diterapkan agar tidak melampaui batas Telegram.

## 6. Kebutuhan Non-Fungsional

- **Keamanan**: refresh token terenkripsi, token pairing sekali pakai dan berumur pendek, token bot dan kunci enkripsi di environment variable, setiap aksi diverifikasi terhadap `chat_id`.
- **Keandalan**: kegagalan satu pengguna atau satu video tidak menghentikan siklus pengguna lain. Kesalahan jaringan memicu percobaan ulang terbatas.
- **Efisiensi**: panggilan YouTube API per siklus diminimalkan (satu `videos.list` untuk semua video).
- **Ketersediaan**: proses bot dan scheduler harus selalu aktif di hosting.
- **Privasi**: pesan Telegram hanya memuat cuplikan komentar secukupnya. Data yang disimpan hanya yang diperlukan.

## 7. Perubahan Data

### Tabel baru

| Tabel | Kolom utama |
|---|---|
| `telegram_links` | `user_id`, `chat_id`, `paused`, `min_alert_count`, `created_at` |
| `pairing_tokens` | `token_hash`, `user_id`, `expires_at`, `used_at` |
| `monitored_videos` | `user_id`, `video_id`, `last_comment_count`, `last_checked_at`, `active` |
| `patrol_runs` (log) | `user_id`, `run_at`, `videos_checked`, `est_api_units`, `new_comments`, `alerts_sent`, `error` |

### Perubahan tabel yang sudah ada

Tabel komentar ditambah kolom: `label`, `score`, `notified`.

## 8. Alur Utama

1. Pengguna login di web, menekan "Hubungkan Telegram", membuka tautan, dan menekan Start (validasi dan penyimpanan pasangan dikerjakan sistem).
2. Scheduler memicu patroli. Sistem membaca `commentCount` dan mengambil komentar baru hanya untuk video yang berubah.
3. Komentar baru diklasifikasikan, lalu ringkasan dikirim ke Telegram jika ada temuan.
4. Pengguna menekan **[Tinjau di web]** dan melakukan review serta reject di web.

## 9. Metrik Keberhasilan

- Pairing selesai dalam kurang dari satu menit sejak tombol di web ditekan.
- Notifikasi tiba dalam waktu sekitar satu interval polling setelah komentar muncul.
- Tidak ada notifikasi ganda untuk komentar yang sama.
- Konsumsi kuota per pengguna per hari tercatat dan sesuai estimasi (jauh di bawah polling tanpa pengecekan `commentCount`).
- Patroli berhenti dan memberi tahu pengguna dengan benar pada kasus `invalid_grant` dan kuota habis.

## 10. Risiko dan Mitigasi

| Risiko | Mitigasi |
|---|---|
| Refresh token kedaluwarsa 7 hari (mode Testing) | Deteksi `invalid_grant`, pesan login ulang, daftarkan penguji |
| Kuota YouTube per project habis | Cek `commentCount` lebih dulu, interval adaptif, jeda otomatis |
| `commentCount` tidak akurat (ikut menghitung balasan, naik-turun bersamaan) | Bandingkan dengan kondisi "berbeda", pengecekan penuh berkala |
| Hosting tidur sehingga patroli berhenti | Gunakan hosting dengan proses yang selalu aktif |
| Banjir notifikasi | Satu ringkasan per video per siklus, ambang notifikasi, batas laju |
| Akses oleh orang lain ke bot | Verifikasi `chat_id` dan `user_id` di setiap command |

## 11. Pemecahan Task

Urutan pengerjaan disusun agar setiap task bisa diuji sendiri. Task T4 sampai T6 bergantung pada T2 dan T3.

### T1: Persiapan bot dan konfigurasi

- Buat bot lewat BotFather, simpan token di environment variable.
- Pilih library (`python-telegram-bot` dengan `JobQueue`, atau `aiogram` + `APScheduler`) dan mode (long polling cukup untuk tugas ini).
- Daftarkan daftar command ke BotFather.
- **Selesai jika**: bot merespons `/bantuan` dan prosesnya berjalan stabil.

### T2: Pairing akun

- Endpoint web pembuat token sekali pakai, tombol "Hubungkan Telegram", dan tabel `pairing_tokens`.
- Handler `/start <token>`: validasi, simpan `telegram_links`, tandai token terpakai.
- Penanganan token tidak valid, kedaluwarsa, atau sudah dipakai.
- **Selesai jika**: tautan dari web menghubungkan akun, token tidak bisa dipakai dua kali, token kedaluwarsa ditolak.

### T3: Manajemen token Google dan sesi

- Penyimpanan refresh token terenkripsi dan fungsi penukar access token.
- Deteksi `invalid_grant`: tandai sesi tidak valid, hentikan patroli pengguna, kirim pesan login ulang.
- **Selesai jika**: refresh token yang dicabut menghasilkan pesan login ulang, bukan error diam-diam.

### T4: Patroli dan pengecekan `commentCount`

- Scheduler per pengguna aktif, pengambilan daftar video terbaru, panggilan `videos.list` (statistics).
- Tabel `monitored_videos`: baseline siklus pertama, perbandingan `commentCount`, simpan nilai terbaru.
- Pengambilan komentar baru dengan `commentThreads.list` sampai bertemu `comment_id` yang sudah ada, lalu upsert ke database.
- Lewati video yang komentarnya dinonaktifkan.
- **Selesai jika**: komentar baru terambil hanya saat `commentCount` berubah, dan siklus pertama tidak mengambil komentar lama.

### T5: Klasifikasi komentar baru dengan SVM

- Hubungkan hasil T4 ke pipeline normalisasi dan SVM yang sudah ada.
- Simpan `label` dan `score`, kelompokkan judol, perlu review, normal.
- **Selesai jika**: setiap komentar baru memiliki label dan skor di database.

### T6: Notifikasi

- Penyusun pesan ringkasan per video dengan cuplikan komentar dan tombol **[Tinjau di web]**.
- Penandaan `notified`, ambang notifikasi, dan pembatasan laju kirim.
- Penanganan bot yang diblokir pengguna (hentikan patroli dan tandai tidak aktif).
- **Selesai jika**: satu ringkasan per video per siklus, tidak ada duplikat, dan tombol membuka halaman review yang benar.

### T7: Command pemantauan

- `/status`, `/stats`, `/topspammer`, `/pause`, `/resume`, `/putuskan`, `/bantuan`.
- Semua query difilter berdasarkan `user_id` dari `chat_id`.
- **Selesai jika**: setiap command menghasilkan jawaban yang benar untuk akun sendiri, dan `/pause` benar-benar menghentikan notifikasi.

### T8: Pengendalian kuota dan ketahanan

- Estimasi dan pencatatan unit API ke `patrol_runs`.
- Penanganan `quotaExceeded` (jeda sampai reset) dan percobaan ulang terbatas untuk kesalahan jaringan.
- Isolasi kegagalan antarpengguna dan antarvideo.
- **Selesai jika**: kuota habis menjeda patroli tanpa crash, dan error satu pengguna tidak memengaruhi pengguna lain.

### T9: Deployment dan operasional

- Jalankan bot dan scheduler sebagai proses yang selalu aktif (VPS atau hosting non-tidur), konfigurasi environment, dan log.
- Mulai ulang otomatis jika proses mati.
- **Selesai jika**: patroli tetap berjalan setelah proses di-restart dan log siklus dapat dibaca.

### T10: Pengujian dan skenario demo

- Uji: pairing valid dan tidak valid, siklus pertama (baseline), `commentCount` berubah dan tidak berubah, komentar judol baru, `invalid_grant`, kuota habis, `/pause`.
- Siapkan skenario demo: unggah komentar uji di video milik sendiri, lalu tunjukkan notifikasi dan tautan ke web.
- **Selesai jika**: semua skenario lulus dan demo berjalan dari awal sampai akhir.

## 12. Dependensi

- Web yang sudah ada: login OAuth, halaman review video (target tautan **[Tinjau di web]**), tabel komentar.
- Model SVM beserta normalisasi teks yang sudah dilatih.
- Hosting dengan proses yang selalu aktif.

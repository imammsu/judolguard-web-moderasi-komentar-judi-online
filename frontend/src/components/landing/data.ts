import type { ZoneType } from './primitives';

export interface SampleComment {
  id: string;
  author: string;
  ago: string;
  textOriginal: string;
  detectedPattern: string;
  zone: ZoneType;
  score: number;
  ruleHit: boolean;
  explanation: string;
}

/**
 * Sampel komentar YouTube dengan penjelasan ramah kreator (tanpa istilah teknis belakang layar).
 */
export const SAMPLE_COMMENTS: SampleComment[] = [
  {
    id: 'c1',
    author: '@sultan_maxwin88',
    ago: 'baru saja',
    textOriginal: 'Main di 𝗚𝗔𝗖𝗢𝗥77 pasti maxwin bosku, modal receh auto WD!',
    detectedPattern: 'Nama situs judol dengan huruf bergaya + ajakan menang',
    zone: 'judol',
    score: 0.998,
    ruleHit: true,
    explanation: 'Mengandung promosi nama situs judi online dengan huruf tebal samaran dan kata kunci khas spam.',
  },
  {
    id: 'c2',
    author: '@info_hoki_4d',
    ago: '1m lalu',
    textOriginal: 'p4s4d 4d wd cepat, daftar lewat WA 0812-3456-7890',
    detectedPattern: 'Samaran angka (p4s4d) + nomor kontak pendaftaran',
    zone: 'judol',
    score: 0.99,
    ruleHit: true,
    explanation: 'Menyebutkan situs togel/4D dengan angka pengganti huruf disertai nomor WhatsApp promosi.',
  },
  {
    id: 'c3',
    author: '@rizky_pratama',
    ago: '2m lalu',
    textOriginal: 'Mantap bang tutorialnya, sangat membantu buat pemula!',
    detectedPattern: 'Komentar apresiasi penonton asli',
    zone: 'bukan',
    score: 0.015,
    ruleHit: false,
    explanation: 'Tanggapan normal dari penonton video Anda — aman dan tidak terindikasi spam.',
  },
  {
    id: 'c4',
    author: '@pejuang_cuan',
    ago: '3m lalu',
    textOriginal: 'info link gacor ketik di google aja bang',
    detectedPattern: 'Ajakan mencari situs di Google tanpa menyebut nama brand',
    zone: 'review',
    score: 0.286,
    ruleHit: true,
    explanation: 'Pola promosi terselubung tanpa nama situs langsung. Dimasukkan ke Perlu Review agar Anda tinjau dulu.',
  },
  {
    id: 'c5',
    author: '@dinda_kurnia',
    ago: '4m lalu',
    textOriginal: 'Kak, bagian pasang PSU di menit 12 itu kabelnya yang mana ya?',
    detectedPattern: 'Pertanyaan penonton seputar isi video',
    zone: 'bukan',
    score: 0.002,
    ruleHit: false,
    explanation: 'Pertanyaan normal dari penonton meskipun memuat angka menit — aman di kategori Bukan Judol.',
  },
  {
    id: 'c6',
    author: '@agen_resmi99',
    ago: '5m lalu',
    textOriginal: 'wisdomtoto bonus new member 100% daftar sekarang di link bio',
    detectedPattern: 'Promosi situs + iming-iming bonus member baru',
    zone: 'judol',
    score: 0.999,
    ruleHit: true,
    explanation: 'Menyebut nama situs judol secara eksplisit disertai ajakan daftar dan klaim bonus.',
  },
  {
    id: 'c7',
    author: '@dimas_ari',
    ago: '7m lalu',
    textOriginal: 'Banyak banget spam judol di kolom komentar ini, semangat bersih-bersihnya bang',
    detectedPattern: 'Keluhan penonton tentang maraknya spam',
    zone: 'bukan',
    score: 0.027,
    ruleHit: false,
    explanation: 'Penonton yang mengeluhkan spam tanpa mempromosikan situs tetap dikategorikan aman.',
  },
  {
    id: 'c8',
    author: '@chip_harian',
    ago: '9m lalu',
    textOriginal: 'bonus chip gratis buat member baru, hubungi telegram kami',
    detectedPattern: 'Tawaran bonus chip + ajakan kontak Telegram',
    zone: 'review',
    score: 0.245,
    ruleHit: true,
    explanation: 'Kombinasi ajakan kontak luar dan penawaran bonus dimasukkan ke Perlu Review untuk Anda cek.',
  },
];

export interface KeywordChip {
  keyword: string;
  type: 'situs' | 'kata_kunci';
  frequency: number;
}

export const EXTRACTED_KEYWORDS: KeywordChip[] = [
  { keyword: 'GACOR77', type: 'situs', frequency: 24 },
  { keyword: 'wisdomtoto', type: 'situs', frequency: 18 },
  { keyword: 'p4s4d', type: 'situs', frequency: 14 },
  { keyword: 'PULAUWIN', type: 'situs', frequency: 11 },
  { keyword: 'maxwin', type: 'kata_kunci', frequency: 31 },
  { keyword: 'slot gacor', type: 'kata_kunci', frequency: 22 },
  { keyword: 'bonus chip gratis', type: 'kata_kunci', frequency: 9 },
  { keyword: 'auto WD', type: 'kata_kunci', frequency: 8 },
];

export interface ChatPreset {
  id: string;
  label: string;
  question: string;
  summaryLabel: string;
  answerTitle: string;
  rows: { col1: string; col2: string; badge: string }[];
}

export const CHAT_PRESETS: ChatPreset[] = [
  {
    id: 'spammers',
    label: 'Akun paling sering spam?',
    question: 'Akun mana yang paling sering mengirim komentar judol di channel saya?',
    summaryLabel: 'Rekap Pelaku Spam Terbanyak',
    answerTitle: '3 Akun dengan Komentar Judol Terbanyak di Video Anda',
    rows: [
      { col1: '@sultan_maxwin88', col2: 'Terdeteksi di 4 video', badge: '19 komentar judol' },
      { col1: '@agen_resmi99', col2: 'Terdeteksi di 3 video', badge: '14 komentar judol' },
      { col1: '@info_hoki_4d', col2: 'Terdeteksi di 2 video', badge: '11 komentar judol' },
    ],
  },
  {
    id: 'keywords',
    label: 'Situs paling sering muncul?',
    question: 'Nama situs judol apa yang paling banyak muncul minggu ini?',
    summaryLabel: 'Rekap Nama Situs & Kata Spam',
    answerTitle: 'Nama Situs yang Paling Sering Dipromosikan Spammer',
    rows: [
      { col1: 'GACOR77', col2: 'Nama Situs', badge: '24x muncul' },
      { col1: 'wisdomtoto', col2: 'Nama Situs', badge: '18x muncul' },
      { col1: 'p4s4d', col2: 'Nama Situs', badge: '14x muncul' },
    ],
  },
  {
    id: 'hours',
    label: 'Jam berapa spam paling ramai?',
    question: 'Jam berapa komentar judol paling ramai masuk?',
    summaryLabel: 'Pola Waktu Komentar Spam',
    answerTitle: 'Jam Puncak Masuknya Komentar Judol (WIB)',
    rows: [
      { col1: '21:00 – 23:59 WIB', col2: 'Malam hari', badge: '46% dari total spam' },
      { col1: '00:00 – 03:00 WIB', col2: 'Dini hari', badge: '31% dari total spam' },
      { col1: '12:00 – 14:00 WIB', col2: 'Siang hari', badge: '12% dari total spam' },
    ],
  },
  {
    id: 'videos',
    label: 'Video paling banyak spam?',
    question: 'Video mana di channel saya yang paling banyak komentar judolnya?',
    summaryLabel: 'Perbandingan Antar Video',
    answerTitle: 'Video dengan Jumlah Komentar Judol Terbanyak',
    rows: [
      { col1: 'Vlog Kuliner Malam Jogja', col2: '1.240 total komentar', badge: '42 komentar judol' },
      { col1: 'Rakit PC Gaming 8 Jutaan', col2: '980 total komentar', badge: '29 komentar judol' },
      { col1: 'Tips Edit Video di Laptop', col2: '610 total komentar', badge: '11 komentar judol' },
    ],
  },
];

export interface PlatformTourTab {
  label: string;
  kind: 'scan' | 'review' | 'keywords' | 'chatbot';
  icon: string;
  title: string;
  points: { title: string; text: string }[];
}

export const PLATFORM_TABS: PlatformTourTab[] = [
  {
    label: '1. Pilih & Scan Video',
    kind: 'scan',
    icon: 'bolt',
    title: 'Pilih video channel Anda,\npindai ratusan komentar seketika.',
    points: [
      {
        title: 'Daftar video langsung dari channel YouTube Anda',
        text: 'Menampilkan judul, thumbnail, tanggal tayang, dan jumlah komentar dari setiap video di channel Anda.',
      },
      {
        title: 'Pindai komentar hanya pada video yang Anda pilih',
        text: 'Klik tombol Scan saat Anda ingin memeriksa video tertentu sehingga pemakaian kuota tetap hemat.',
      },
      {
        title: 'Proses cepat untuk ribuan komentar',
        text: 'Seluruh komentar diambil dan langsung dikelompokkan dalam hitungan detik.',
      },
    ],
  },
  {
    label: '2. Review 3 Zona & Reject',
    kind: 'review',
    icon: 'shield',
    title: 'AI memberi rekomendasi,\nAnda yang memegang keputusan.',
    points: [
      {
        title: 'Dipisahkan ke tiga kategori yang jelas',
        text: 'Komentar dibagi menjadi Judol, Perlu Review (ragu-ragu), dan Bukan Judol agar komentar penonton asli tetap aman.',
      },
      {
        title: 'Koreksi label dengan satu klik',
        text: 'Jika ada komentar yang ingin Anda ubah kategorinya, cukup klik tombol koreksi sebelum melakukan reject.',
      },
      {
        title: 'Reject massal setelah konfirmasi Anda',
        text: 'Tolak satu per satu, beberapa yang dipilih, atau seluruh komentar judol sekaligus dari tampilan publik YouTube.',
      },
    ],
  },
  {
    label: '3. Kata Kunci Blokir',
    kind: 'keywords',
    icon: 'tag',
    title: 'Salin daftar nama situs spam\nke YouTube Studio.',
    points: [
      {
        title: 'Kumpulkan nama situs & istilah judol otomatis',
        text: 'AI merangkum nama-nama situs dan kata promosi yang paling sering dipakai spammer di video Anda.',
      },
      {
        title: 'Sesuai dengan kata yang benar-benar muncul',
        text: 'Setiap kata kunci diambil langsung dari tulisan asli di komentar spam beserta jumlah kemunculannya.',
      },
      {
        title: 'Siap ditempel ke fitur Blocked Words',
        text: 'Centang kata yang diinginkan lalu klik Salin untuk langsung ditempel ke pengaturan moderasi YouTube Studio.',
      },
    ],
  },
  {
    label: '4. Chatbot Analisis Spam',
    kind: 'chatbot',
    icon: 'chat',
    title: 'Tanya pola pelaku spam\ntanpa cek manual satu-satu.',
    points: [
      {
        title: 'Temukan akun penyebar spam paling aktif',
        text: 'Ketahui akun mana saja yang berulang kali mengirim komentar promosi judol di berbagai video Anda.',
      },
      {
        title: 'Tersedia tombol pertanyaan cepat',
        text: 'Klik topik pertanyaan populer atau ketik pertanyaan Anda sendiri dalam bahasa sehari-hari.',
      },
      {
        title: 'Jawaban akurat dari data komentar channel Anda',
        text: 'Seluruh angka dan daftar akun dihitung langsung dari hasil pemindaian video di channel Anda sendiri.',
      },
    ],
  },
];

export const SECURITY_ITEMS = [
  {
    icon: 'lock',
    title: 'Login Resmi Akun Google & YouTube',
    text: 'Masuk dengan aman melalui halaman izin resmi Google tanpa pernah memberikan password akun YouTube Anda kepada aplikasi.',
  },
  {
    icon: 'hand',
    title: 'Tidak Ada Penghapusan Otomatis',
    text: 'Sistem tidak pernah menyembunyikan atau menolak komentar secara diam-diam. Setiap tindakan reject selalu meminta konfirmasi Anda.',
  },
  {
    icon: 'shield',
    title: 'Data Channel Terisolasi & Privat',
    text: 'Komentar, daftar kata kunci, dan hasil analisis hanya dapat diakses oleh akun pemilik channel yang bersangkutan.',
  },
  {
    icon: 'clock',
    title: 'Pembersihan Otomatis & Kendali Data',
    text: 'Data komentar yang tersimpan lebih dari 30 hari dibersihkan otomatis, dan Anda dapat menghapus seluruh data kapan saja.',
  },
];

export const FAQ_ITEMS = [
  {
    q: 'Apakah JudolGuard langsung menghapus komentar secara otomatis?',
    a: 'Tidak pernah. Prinsip utama JudolGuard adalah "AI memberi rekomendasi, manusia memutuskan". Semua komentar dikelompokkan dulu ke tiga zona (Judol, Perlu Review, dan Bukan Judol), lalu hanya di-reject setelah Anda meninjau dan menekan tombol konfirmasi.',
  },
  {
    q: 'Bagaimana jika spammer memakai huruf unik atau spasi berjarak seperti "𝗚 𝗔 𝗖 𝗢 𝗥"?',
    a: 'AI JudolGuard secara otomatis mengenali huruf bergaya (Unicode), angka pengganti huruf, spasi berjarak, hingga nama situs baru yang belum pernah muncul sebelumnya, sehingga tetap masuk ke kategori Judol.',
  },
  {
    q: 'Kenapa ada kategori "Perlu Review" selain "Judol" dan "Bukan Judol"?',
    a: 'Kategori Perlu Review dibuat untuk melindungi komentar penonton asli. Komentar yang sifatnya samar—misalnya tidak menyebut nama situs tapi mengajak mencari di Google atau menghubungi kontak tertentu—dipisahkan ke Perlu Review agar bisa Anda periksa lebih dulu.',
  },
  {
    q: 'Untuk apa fitur Ekstraksi Kata Kunci di JudolGuard?',
    a: 'Di YouTube Studio terdapat fitur "Blocked words" untuk menahan komentar yang mengandung kata tertentu. JudolGuard merangkum nama-nama situs dan istilah judol yang sedang ramai di video Anda dalam format dipisah koma, sehingga Anda tinggal menyalin dan menempelkannya ke YouTube Studio.',
  },
  {
    q: 'Apa saja yang bisa saya tanyakan ke Chatbot Analisis Spam?',
    a: 'Anda bisa menanyakan akun mana yang paling sering mengirim spam, berapa jumlah dan persentase komentar judol, nama situs apa yang paling sering muncul, jam berapa serangan spam paling ramai, hingga video mana yang paling banyak terkena spam.',
  },
  {
    q: 'Apakah saya bisa menghapus seluruh data komentar channel saya dari JudolGuard?',
    a: 'Bisa kapan saja. Selain pembersihan otomatis setiap 30 hari, tersedia fitur "Hapus Data Saya" untuk menghapus seluruh riwayat komentar, kata kunci, dan mencabut akses akun YouTube Anda.',
  },
];

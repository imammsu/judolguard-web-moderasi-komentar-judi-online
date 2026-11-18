
import re
import unicodedata

URL_RE   = re.compile(r"(https?://\S+|www\.\S+|\b\S+\.(?:com|net|org|xyz|top|site|online|id|co|me|vip|bet)\b\S*)")
PHONE_RE = re.compile(r"(?:\+?62|0)\s?8[\d\s\-\.]{7,14}\d")
MENTION_RE = re.compile(r"@\S+")
EMOJI_CODE_RE = re.compile(r":[a-z_]+:")
SPACED_RE = re.compile(r"(?<![a-z0-9])(?:[a-z0-9]\s){2,}[a-z0-9](?![a-z0-9])")
LEET = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t"}
LEET_RE = re.compile(r"(?<=[a-z])[013457](?=[a-z])")
REPEAT_RE = re.compile(r"(.)\1{2,}")

# huruf mirip (Yunani/Sirilik) dan angka dingbat -> Latin/angka biasa
_HOMO_SRC = {"ο": "o", "в": "b", "е": "e", "а": "a", "р": "p",
             "с": "c", "х": "x", "у": "y", "і": "i", "ѕ": "s"}
for _base in (0x2776, 0x2780, 0x278A):
    for _i in range(10):
        _HOMO_SRC[chr(_base + _i)] = str((_i + 1) % 10)
HOMO = str.maketrans(_HOMO_SRC)

def _unspace(m):
    s = m.group(0)
    return re.sub(r"\s", "", s) if re.search(r"[a-z]", s) else s

def normalize(text, full=True):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = "".join(c for c in text if unicodedata.category(c) not in ("Mn", "Cf"))   # buang tanda gabung + zero-width
    text = text.lower()
    if not full:
        return re.sub(r"\s+", " ", text).strip()
    text = text.translate(HOMO)
    text = MENTION_RE.sub(" ", text)
    text = EMOJI_CODE_RE.sub(" ", text)
    text = URL_RE.sub(" urltoken ", text)
    text = PHONE_RE.sub(" phonetoken ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)       # simbol/pemisah -> spasi
    text = SPACED_RE.sub(_unspace, text)           # gabung huruf tunggal berderet
    for _ in range(2):
        text = LEET_RE.sub(lambda m: LEET[m.group(0)], text)
    text = REPEAT_RE.sub(r"\1\1", text)
    return re.sub(r"\s+", " ", text).strip()

# ---------- masking brand judol ----------
# alexis17, sgi88, mandalika77 (minimal 3 huruf; kode mobil seperti ae86/rb26/cx90 TIDAK di-mask) | agustoto, wisdomtoto, bwtogel | pulauwin (kecuali maxwin/makswin/mekswin)
BRAND_RE = re.compile(
    r"\b(?:[a-z]{3,}\d{2,3}(?!\d)"
    r"|(?:[a-z]{3,}(?:toto|togel)"
    r"|(?!(?:max|maks|meks|mex)win\b)[a-z]{3,}win)\b)")
# pola "pas4d": harus diganti SEBELUM leet-normalisasi mengubah 4 -> a
BRAND4D_RE = re.compile(r"\b[a-z]{2,}\s?4d\b")
_PREFIX_RE = re.compile(r"^(?:di|sibuk|dari|ke|se|pake|pakai)(?=[a-z]{3,}\d)")

def mask_brand(text_norm):
    return BRAND_RE.sub(" brandtoken ", text_norm).strip()

def _pre(text):
    text = unicodedata.normalize("NFKC", text)
    text = "".join(c for c in text if unicodedata.category(c) not in ("Mn", "Cf"))
    return text.lower()

def brand_of(text):
    # menerima teks MENTAH; mengembalikan nama brand pertama atau "_none"
    if not isinstance(text, str):
        return "_none"
    raw = _pre(text)
    m4 = BRAND4D_RE.search(raw)
    if m4:
        return m4.group(0)
    m = BRAND_RE.search(normalize(raw))
    if not m:
        return "_none"
    b = _PREFIX_RE.sub("", m.group(0))
    return "alexis17" if b in ("lexis17", "alexis17") else b

def prepare(text):
    # PINTU MASUK model (dipakai notebook DAN aplikasi): normalisasi + masking brand
    if not isinstance(text, str):
        return ""
    raw = BRAND4D_RE.sub(" brandtoken ", _pre(text))
    return re.sub(r"\s+", " ", mask_brand(normalize(raw))).strip()

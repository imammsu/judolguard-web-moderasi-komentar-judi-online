"""Pemuat model ML (singleton per proses) dan klasifikasi satu array.

- Model ``judol_model.joblib`` dan ``metrics.json`` dimuat SEKALI per proses
  (PRD 8.7). Gunicorn dengan beberapa worker memuat satu salinan per worker.
- Hash SHA-256 ``normalizer.py`` dibandingkan dengan ``metrics.json``
  (PRD 14.3); bila berbeda, dicatat peringatan dan ``/health`` melaporkannya.
- ``classify_array()`` mengklasifikasikan seluruh komentar sekaligus dalam
  SATU panggilan ``model.predict_proba`` setelah ``prepare()`` dan dedup
  (PRD 8.2). Dipakai oleh alur Scan pada Part 5.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import sklearn

from .normalizer import prepare
from .rules import check_rule_hit

logger = logging.getLogger(__name__)

ML_DIR = Path(__file__).resolve().parent
MODEL_DIR = ML_DIR / "model"
MODEL_PATH = MODEL_DIR / "judol_model.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"
NORMALIZER_PATH = ML_DIR / "normalizer.py"

ZONE_JUDOL = "judol"
ZONE_REVIEW = "review"
ZONE_BUKAN = "bukan"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ClassificationResult:
    text_prepared: str
    text_hash: str
    score: float
    zone: str
    rule_hit: bool
    model_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MLModelRegistry:
    """Singleton yang menyimpan model, metrik, dan status verifikasi."""

    _instance: MLModelRegistry | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.model: Any = None
        self.metrics: dict[str, Any] = {}
        self.normalizer_hash: str | None = None
        self.loaded_at: float | None = None
        self.load_error: str | None = None
        self.load_seconds: float | None = None

    # ---------- siklus hidup ----------
    @classmethod
    def instance(cls) -> MLModelRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def load(self) -> None:
        """Muat model bila belum dimuat. Aman dipanggil berkali-kali."""
        if self.is_loaded:
            return
        with self._lock:
            if self.is_loaded:
                return
            start = time.perf_counter()
            try:
                self.metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
                self.normalizer_hash = sha256_file(NORMALIZER_PATH)
                self.model = joblib.load(MODEL_PATH)
                self.loaded_at = time.time()
                self.load_error = None
            except Exception as exc:  # noqa: BLE001 - dilaporkan lewat /health
                self.model = None
                self.load_error = f"{type(exc).__name__}: {exc}"
                logger.exception("Gagal memuat model ML")
                return
            self.load_seconds = round(time.perf_counter() - start, 3)

        logger.info(
            "Model ML dimuat (%s) dalam %.2f detik",
            self.model_version,
            self.load_seconds or 0,
        )
        if not self.normalizer_match:
            logger.warning(
                "Hash normalizer.py TIDAK cocok dengan metrics.json "
                "(sekarang=%s, diharapkan=%s). Hasil model bisa berbeda dari notebook.",
                self.normalizer_hash,
                self.expected_normalizer_hash,
            )
        if not self.sklearn_version_match:
            logger.warning(
                "Versi scikit-learn %s berbeda dari versi training %s.",
                sklearn.__version__,
                self.expected_sklearn_version,
            )

    # ---------- metadata ----------
    @property
    def model_version(self) -> str:
        return str(self.metrics.get("model_version", "unknown"))

    @property
    def expected_normalizer_hash(self) -> str | None:
        return self.metrics.get("normalizer_sha256")

    @property
    def normalizer_match(self) -> bool:
        return bool(self.normalizer_hash) and self.normalizer_hash == self.expected_normalizer_hash

    @property
    def expected_sklearn_version(self) -> str | None:
        return self.metrics.get("sklearn_version")

    @property
    def sklearn_version_match(self) -> bool:
        return sklearn.__version__ == self.expected_sklearn_version

    @property
    def t_low(self) -> float:
        return float(self.metrics["thresholds"]["t_low"])

    @property
    def t_high(self) -> float:
        return float(self.metrics["thresholds"]["t_high"])

    def status(self) -> dict[str, Any]:
        thresholds = None
        if self.metrics.get("thresholds"):
            thresholds = {"t_low": self.t_low, "t_high": self.t_high}
        return {
            "model_loaded": self.is_loaded,
            "model_version": self.model_version,
            "load_error": self.load_error,
            "load_seconds": self.load_seconds,
            "sklearn_version": sklearn.__version__,
            "expected_sklearn_version": self.expected_sklearn_version,
            "sklearn_version_match": self.sklearn_version_match,
            "normalizer_hash": self.normalizer_hash,
            "expected_normalizer_hash": self.expected_normalizer_hash,
            "normalizer_match": self.normalizer_match,
            "thresholds": thresholds,
        }

    # ---------- inferensi ----------
    def zone_for(self, score: float, rule_hit: bool) -> str:
        if score >= self.t_high:
            return ZONE_JUDOL
        if score >= self.t_low:
            return ZONE_REVIEW
        # Aturan hanya menaikkan "bukan" -> "review", tidak pernah ke "judol".
        return ZONE_REVIEW if rule_hit else ZONE_BUKAN

    def classify_array(self, texts: list[str]) -> list[ClassificationResult]:
        """Klasifikasikan seluruh teks sekaligus.

        1. ``prepare()`` untuk setiap teks (wajib, PRD 9.2).
        2. Dedup berdasarkan hash teks hasil ``prepare()``.
        3. SATU kali ``predict_proba`` untuk seluruh teks unik.
        4. Petakan hasil kembali ke semua duplikat, terapkan ambang + aturan.
        """
        if not self.is_loaded:
            raise RuntimeError("Model ML belum dimuat")
        if not texts:
            return []

        prepared = [prepare(t) for t in texts]
        hashes = [sha256_text(p) for p in prepared]

        unique: dict[str, str] = {}
        for h, p in zip(hashes, prepared, strict=True):
            unique.setdefault(h, p)

        unique_hashes = list(unique.keys())
        probs = self.model.predict_proba(list(unique.values()))[:, 1]
        score_by_hash = {h: float(s) for h, s in zip(unique_hashes, probs, strict=True)}

        results: list[ClassificationResult] = []
        for original, p, h in zip(texts, prepared, hashes, strict=True):
            score = score_by_hash[h]
            rule_hit = check_rule_hit(original, p)
            results.append(
                ClassificationResult(
                    text_prepared=p,
                    text_hash=h,
                    score=round(score, 6),
                    zone=self.zone_for(score, rule_hit),
                    rule_hit=rule_hit,
                    model_version=self.model_version,
                )
            )
        return results


def get_registry() -> MLModelRegistry:
    return MLModelRegistry.instance()

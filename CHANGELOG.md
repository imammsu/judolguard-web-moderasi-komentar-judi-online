# Changelog

Format mengikuti [Keep a Changelog](https://keepachangelog.com/id-ID/1.1.0/) dan versi per part PRD.

## [0.1.0] - 2026-11-18 — Part 1: Fondasi Aplikasi

### Ditambahkan
- Struktur repositori sesuai PRD 8.6 (`backend/`, `frontend/`, `docs/`, `notebooks/`).
- Artefak ML dipindah ke `backend/app/ml/model/` (`judol_model.joblib`, `metrics.json`) dan `backend/app/ml/normalizer.py`.
- `metrics.json` ditambah `model_version` dan `normalizer_sha256`.
- `backend/app/ml/rules.py`: lapisan aturan iklan tanpa brand dan kontak + ajakan (hanya menaikkan "bukan" → "review").
- `backend/app/ml/loader.py`: singleton model (dimuat sekali per proses), verifikasi hash `normalizer.py` dan versi scikit-learn, serta `classify_array()` (satu panggilan `predict_proba` untuk seluruh komentar unik).
- Backend Flask: application factory, konfigurasi dari `.env` (opsi pool Supabase Session Mode Pooler), respons JSON seragam, error handler JSON, logging, Blueprint kosong per modul, endpoint `/health` dan `/api/health`, penyajian `frontend/dist`.
- Frontend Vite + React + TypeScript + Tailwind CSS v4 + React Router + TanStack Query, klien API bertipe, proxy Vite ke Flask, beranda status backend & model.
- Perkakas: Ruff, Pytest, ESLint, Prettier, skrip `run-backend.ps1` dan `run-frontend.ps1`.
- `.env.example` dan `.env` lokal (kredensial masih kosong).

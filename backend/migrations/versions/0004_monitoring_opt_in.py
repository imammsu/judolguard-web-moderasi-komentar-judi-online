"""Ubah monitoring Sentinel menjadi opt-in per video."""

from __future__ import annotations

from alembic import op

revision = "0004_monitoring_opt_in"
down_revision = "0003_sentinel_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Record lama dibuat otomatis dari lima video terbaru. Nonaktifkan tanpa
    # menghapus baseline agar pengguna dapat memilih ulang dari Telegram.
    op.execute("UPDATE monitored_videos SET active = false WHERE active = true")


def downgrade() -> None:
    # Tidak mengaktifkan kembali target lama secara otomatis karena status
    # pilihan pengguna tidak dapat direkonstruksi dengan aman.
    pass

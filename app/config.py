"""Konfigurasi aplikasi. Semua nilai dapat diubah lewat environment variable."""
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
SNAP = DATA / "snapshots"      # snapshot bukti pelanggaran
UPLOAD = DATA / "uploads"      # video yang diunggah pengguna
for _p in (SNAP, UPLOAD):
    _p.mkdir(parents=True, exist_ok=True)

DB_URL = os.getenv("DB_URL", f"sqlite:///{DATA / 'apd.db'}")
MODEL_PATH = os.getenv("MODEL_PATH", str(BASE / "models" / "best.pt"))
CONF = float(os.getenv("CONF", "0.4"))            # confidence threshold YOLO
IMGSZ = int(os.getenv("IMGSZ", "640"))            # ukuran input inferensi
MAX_WIDTH = int(os.getenv("MAX_WIDTH", "960"))    # frame lebih lebar akan diperkecil
MIN_FRAMES = int(os.getenv("MIN_FRAMES", "5"))    # pelanggaran harus bertahan N frame
COOLDOWN = float(os.getenv("COOLDOWN", "30"))     # jeda (detik) sebelum pelanggaran yg sama dicatat lagi
SAMPLE_EVERY = float(os.getenv("SAMPLE_EVERY", "5"))  # interval pencatatan statistik kepatuhan (detik)

SECRET_KEY = os.getenv("SECRET_KEY", "ganti-secret-ini-sebelum-dipakai")
TOKEN_TTL = int(os.getenv("TOKEN_TTL", str(8 * 3600)))
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")

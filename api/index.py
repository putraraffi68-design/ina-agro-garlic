"""Entry point untuk Vercel (serverless). Semua URL diarahkan ke sini oleh vercel.json."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
os.environ.setdefault("AGROGARLIC_DB", "/tmp/agrogarlic.db")  # di Vercel hanya /tmp yang boleh ditulis
os.environ.setdefault("DATA_MODE", "riil")

from main import app  # noqa: E402,F401

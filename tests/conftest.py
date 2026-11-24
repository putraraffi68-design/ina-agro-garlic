import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
os.environ["AGROGARLIC_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.setdefault("DATA_MODE", "contoh")  # tes deterministik & tanpa internet

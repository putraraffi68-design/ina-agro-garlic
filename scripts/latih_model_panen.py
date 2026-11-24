"""Melatih model ML prediksi hasil panen. Jalankan: python scripts/latih_model_panen.py"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import prediksi_panen  # noqa: E402

print(json.dumps(prediksi_panen.latih(), indent=1, ensure_ascii=False))

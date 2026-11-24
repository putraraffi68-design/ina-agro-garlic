"""
Backend INA Agro-GARLIC (FastAPI).
Menjalankan:  uvicorn main:app --reload   (dari folder app/)
Dokumentasi API otomatis: http://localhost:8000/docs
"""
import json
import secrets
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import data_spasial
import db
import prediksi_panen
from laporan_pdf import buat_pdf
from rekomendasi import buat_rekomendasi
from rule_engine import DAFTAR_PARAMETER, KRITERIA, PARAM, klasifikasi

app = FastAPI(title="INA Agro-GARLIC API", version="1.0.0",
              description="Analisis kesesuaian lahan bawang putih (rule-based, FAO 1976/BBSDLP)")
STATIC = Path(__file__).parent / "static"
db.init()


# ---------- model request ----------
class AnalisisIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    user_id: Optional[str] = None
    consent: bool = False
    parameter_manual: dict = Field(default_factory=dict,
                                   description="opsional, dari uji tanah sendiri, mis. {'ph_tanah': 5.3}")


class DaftarIn(BaseModel):
    nama: str = ""
    kontak: str
    sandi: str = Field(..., min_length=6)
    consent: bool = False


class MasukIn(BaseModel):
    kontak: str
    sandi: str


class ConsentIn(BaseModel):
    consent: bool


def _token(authorization):
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:]
    return None


def _user_wajib(authorization):
    u = db.user_dari_token(_token(authorization))
    if not u:
        raise HTTPException(401, {"error": "silakan masuk terlebih dahulu"})
    return u


# ---------- akun & consent ----------
@app.post("/api/v1/auth/daftar")
def daftar(body: DaftarIn):
    if not body.kontak.strip():
        raise HTTPException(400, {"error": "No. HP / email wajib diisi"})
    if db.daftar(body.nama, body.kontak, body.sandi, body.consent) is None:
        raise HTTPException(409, {"error": "No. HP / email sudah terdaftar"})
    token = db.masuk(body.kontak, body.sandi)
    return {"token": token, "user": _publik(db.user_dari_token(token))}


@app.post("/api/v1/auth/masuk")
def masuk(body: MasukIn):
    token = db.masuk(body.kontak, body.sandi)
    if not token:
        raise HTTPException(401, {"error": "No. HP/email atau kata sandi salah"})
    return {"token": token, "user": _publik(db.user_dari_token(token))}


@app.post("/api/v1/auth/keluar")
def keluar(authorization: Optional[str] = Header(None)):
    db.keluar(_token(authorization))
    return {"ok": True}


@app.get("/api/v1/akun")
def akun(authorization: Optional[str] = Header(None)):
    return _publik(_user_wajib(authorization))


@app.put("/api/v1/akun/consent")
def ubah_consent(body: ConsentIn, authorization: Optional[str] = Header(None)):
    u = _user_wajib(authorization)
    db.set_consent(u["id"], body.consent)
    return {"consent": body.consent}


def _publik(u):
    return {"id": f"u_{u['id']:04d}", "nama": u["nama"], "kontak": u["kontak"], "consent": bool(u["consent"])}


# ---------- data lokasi & kriteria ----------
@app.get("/api/v1/kriteria")
def kriteria():
    return KRITERIA


@app.get("/api/v1/kawasan")
def kawasan():
    return data_spasial.daftar_kawasan()


@app.get("/api/v1/cari")
def cari(q: str = Query(..., min_length=2)):
    return data_spasial.cari_tempat(q)


def _sumber():
    return data_spasial.sumber_parameter() or {k: PARAM[k]["sumber"] for k in DAFTAR_PARAMETER}


def _ambil_lokasi(lat, lon):
    try:
        d = data_spasial.data_lokasi(lat, lon)
    except Exception:
        raise HTTPException(503, {"error": "sumber data riil (SoilGrids/Open-Meteo) sedang tidak dapat diakses, coba lagi"})
    if d is None:
        msg = "lokasi di luar wilayah Indonesia" if data_spasial.MODE == "riil" else "lokasi di luar kawasan cakupan MVP"
        raise HTTPException(400, {"error": msg})
    if d["nilai"].get("ph_tanah") is None and d["nilai"].get("tekstur") is None and d["asal"] == "langsung":
        raise HTTPException(400, {"error": "tidak ada data tanah di titik ini (kemungkinan laut, danau, atau permukiman padat)"})
    return d


@app.get("/api/v1/info-data")
def info_data():
    return {"mode": data_spasial.MODE, "jumlah_unit": len(data_spasial.UNITS),
            "jumlah_kawasan": len(data_spasial.KAWASAN), "sumber": data_spasial.INFO_SUMBER,
            "sumber_parameter": _sumber()}


@app.get("/api/v1/data-lokasi")
def data_lokasi(lat: float, lon: float):
    d = dict(_ambil_lokasi(lat, lon))
    d.pop("iklim_tahunan", None)
    tersedia = sum(v is not None for v in d["nilai"].values())
    d["kelengkapan_data"] = f"{tersedia}/{len(DAFTAR_PARAMETER)}"
    d["sumber"] = _sumber()
    return d


@app.get("/api/v1/peta-kesesuaian")
def peta_kesesuaian(kawasan_id: Optional[str] = None):
    """Kelas kesesuaian tiap unit lahan (untuk menu Peta)."""
    out = []
    for u in data_spasial.UNITS:
        if kawasan_id and u["kawasan_id"] != kawasan_id:
            continue
        h = klasifikasi(u["nilai"])
        out.append({"id": u["id"], "bbox": u["bbox"], "kelas": h["kelas_akhir"],
                    "faktor_pembatas": h["faktor_pembatas"], "kelengkapan_data": h["kelengkapan_data"]})
    return out


# ---------- analisis (kontrak API LKP 6) ----------
@app.post("/api/v1/analisis")
def analisis(body: AnalisisIn, authorization: Optional[str] = Header(None)):
    t0 = time.perf_counter()
    if not body.consent:
        raise HTTPException(422, {"error": "consent belum diberikan"})
    user = db.user_dari_token(_token(authorization))
    if user and not user["consent"]:
        raise HTTPException(422, {"error": "consent belum diberikan"})

    d = _ambil_lokasi(body.lat, body.lon)

    nilai = dict(d["nilai"])
    sumber = _sumber()
    for k, v in (body.parameter_manual or {}).items():
        if k not in PARAM:
            raise HTTPException(400, {"error": f"parameter tidak dikenal: {k}"})
        if v is None or v == "":
            continue
        if PARAM[k]["jenis"] == "numerik":
            try:
                v = float(v)
            except (TypeError, ValueError):
                raise HTTPException(400, {"error": f"nilai {k} harus angka"})
        else:
            v = str(v).strip().lower()
            if v not in PARAM[k]["pilihan"]:
                raise HTTPException(400, {"error": f"nilai {k} tidak valid: {v}"})
        nilai[k] = v
        sumber[k] = "manual"

    h = klasifikasi(nilai, sumber)
    hasil = {
        "analysis_id": f"an_{datetime.now():%Y%m%d}_{secrets.token_hex(3)}",
        "waktu": datetime.now().isoformat(timespec="seconds"),
        "lokasi": d["lokasi"],
        "elevasi_m": d["elevasi_m"],
        **h,
        "rekomendasi": buat_rekomendasi(h),
        "prediksi_panen": _prediksi_aman(nilai, d["elevasi_m"], (d.get("unit_id") or "").rsplit("-", 2)[0] or None),
    }
    hasil["waktu_proses_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    db.simpan_analisis(hasil, user["id"] if user else None)
    return hasil


def _prediksi_aman(nilai, elev, kawasan_id=None):
    try:
        return prediksi_panen.prediksi(nilai, elev, kawasan_id)
    except Exception:
        return None


@app.get("/api/v1/model-panen")
def model_panen():
    """Informasi model ML prediksi hasil panen (data latih, akurasi, kepentingan fitur)."""
    return prediksi_panen.info_model() or {"tersedia": False}


@app.get("/api/v1/analisis/{aid}")
def ambil(aid: str):
    r = db.ambil_analisis(aid)
    if not r:
        raise HTTPException(404, {"error": "analisis tidak ditemukan"})
    return json.loads(r["hasil"])


@app.get("/api/v1/analisis/{aid}/pdf")
def unduh_pdf(aid: str):
    h = ambil(aid)
    return Response(buat_pdf(h), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="laporan_{aid}.pdf"'})


# ---------- riwayat (F5) ----------
@app.post("/api/v1/riwayat/{aid}")
def simpan(aid: str, authorization: Optional[str] = Header(None)):
    u = _user_wajib(authorization)
    if not db.tandai_disimpan(aid, u["id"]):
        raise HTTPException(404, {"error": "analisis tidak ditemukan"})
    return {"ok": True}


@app.get("/api/v1/riwayat")
def daftar_riwayat(authorization: Optional[str] = Header(None)):
    u = _user_wajib(authorization)
    return db.riwayat(u["id"])


@app.delete("/api/v1/riwayat/{aid}")
def hapus(aid: str, authorization: Optional[str] = Header(None)):
    u = _user_wajib(authorization)
    db.hapus_riwayat(aid, u["id"])
    return {"ok": True}


# ---------- frontend ----------
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")

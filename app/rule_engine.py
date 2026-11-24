"""
Rule engine INA Agro-GARLIC: klasifikasi kesesuaian lahan bawang putih.

Logika sama dengan PoC LKP 6 (poc_kesesuaian_lahan.py):
  - tiap parameter dicocokkan ke rentang kriteria -> kelas S1/S2/S3/N
  - kelas akhir = kelas terburuk dari semua parameter (hukum minimum)
  - parameter dengan kelas terburuk (bukan S1) = faktor pembatas
Tambahan untuk aplikasi: nilai dekat ambang batas, kelengkapan data, penjelasan.
Kriteria dibaca dari data/kriteria_bawang_putih.json supaya bisa dikalibrasi pakar.
"""
import json
from pathlib import Path

KRITERIA_PATH = Path(__file__).parent / "data" / "kriteria_bawang_putih.json"


def muat_kriteria(path=KRITERIA_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


KRITERIA = muat_kriteria()
URUTAN = KRITERIA["urutan_kelas"]
PARAM = KRITERIA["parameter"]
DAFTAR_PARAMETER = list(PARAM.keys())


def kelas_parameter(nama, nilai):
    p = PARAM[nama]
    if p["jenis"] == "kategorik":
        return p["pilihan"].get(str(nilai).strip().lower(), "N")
    for r in p["rentang"]:
        if r["min"] <= nilai < r["max"]:
            return r["kelas"]
    return "N"  # di luar semua rentang


def dekat_ambang(nama, nilai):
    """True bila nilai numerik hanya selisih tipis (<= toleransi) dari batas kelas lain."""
    p = PARAM[nama]
    if p["jenis"] != "numerik":
        return False
    k = kelas_parameter(nama, nilai)
    tol = p.get("toleransi", 0)
    return kelas_parameter(nama, nilai - tol) != k or kelas_parameter(nama, nilai + tol) != k


def arah_penyimpangan(nama, nilai):
    """'rendah' / 'tinggi' untuk numerik di luar rentang S1, nilai kategori untuk kategorik."""
    p = PARAM[nama]
    if p["jenis"] == "kategorik":
        return str(nilai).strip().lower()
    s1 = [r for r in p["rentang"] if r["kelas"] == "S1"]
    if not s1:
        return None
    if nilai < s1[0]["min"]:
        return "rendah"
    if nilai >= s1[0]["max"]:
        return "tinggi"
    return None


def _format_nilai(nama, nilai):
    p = PARAM[nama]
    if p["jenis"] == "kategorik":
        return str(nilai)
    teks = f"{nilai:g}".replace(".", ",")
    return f"{teks}{(' ' if p['satuan'] and p['satuan'][0].isalpha() else '')}{p['satuan']}"


def klasifikasi(unit, sumber=None):
    """
    unit  : dict parameter -> nilai (None = data tidak tersedia)
    sumber: dict parameter -> sumber data (opsional, default dari tabel kriteria)
    Mengembalikan dict sesuai kontrak API LKP 6 (bagian rule engine).
    """
    sumber = sumber or {}
    unit = {k: unit.get(k) for k in DAFTAR_PARAMETER}
    tersedia = {k: v for k, v in unit.items() if v is not None and v != ""}
    hilang = [k for k in DAFTAR_PARAMETER if k not in tersedia]
    if not tersedia:
        raise ValueError("tidak ada data parameter untuk lokasi ini")

    per_param = {}
    for k, v in tersedia.items():
        p = PARAM[k]
        per_param[k] = {
            "nilai": v,
            "ideal": p["ideal"],
            "satuan": p["satuan"],
            "kelas": kelas_parameter(k, v),
            "sumber": sumber.get(k, p["sumber"]),
            "dekat_ambang": dekat_ambang(k, v),
        }

    terburuk = max((d["kelas"] for d in per_param.values()), key=URUTAN.index)
    pembatas = [k for k, d in per_param.items() if d["kelas"] == terburuk and d["kelas"] != "S1"]

    if pembatas:
        alasan = [f"{PARAM[k]['nama']} {_format_nilai(k, unit[k])} (ideal {PARAM[k]['ideal']})"
                  for k in pembatas]
        penjelasan = f"{terburuk} karena " + _gabung(alasan)
    else:
        penjelasan = "Semua parameter yang tersedia memenuhi kriteria S1."

    ada_dekat_ambang = [PARAM[k]["nama"] for k, d in per_param.items() if d["dekat_ambang"]]
    return {
        "kelas_akhir": terburuk,
        "label": KRITERIA["label_kelas"][terburuk],
        "kelas_per_parameter": per_param,
        "faktor_pembatas_kode": pembatas,
        "faktor_pembatas": [PARAM[k]["nama"] for k in pembatas],
        "penjelasan": penjelasan,
        "kelengkapan_data": f"{len(per_param)}/{len(DAFTAR_PARAMETER)}",
        "parameter_hilang": [PARAM[k]["nama"] for k in hilang],
        "parameter_dekat_ambang": ada_dekat_ambang,
        "perlu_verifikasi_lapangan": bool(hilang or ada_dekat_ambang),
    }


def _gabung(daftar):
    if len(daftar) <= 1:
        return "".join(daftar)
    return ", ".join(daftar[:-1]) + " dan " + daftar[-1]

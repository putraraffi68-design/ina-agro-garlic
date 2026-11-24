"""
Lapisan data spasial (pengganti sementara PostGIS).

Mode data (variabel lingkungan DATA_MODE):
  riil   (bawaan bila app/data/unit_lahan_riil.json ada): grid unit lahan riil di 11 sentra
          bawang putih + pengambilan data riil langsung untuk titik lain di Indonesia
  contoh : data dummy 3 kawasan (versi awal prototipe)
Kawasan MVP dibagi jadi petak grid (unit lahan). Tiap petak punya 7 parameter.
Query utama: lokasi (lat, lon) masuk unit lahan mana -> nilai parameternya.

Saat data asli tersedia, cukup ganti fungsi `cari_unit` dengan query PostGIS
(ST_Contains) tanpa mengubah API maupun rule engine.
"""
import json
import math
import os
import random
import threading
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "kawasan_dummy.json"
RIIL_PATH = Path(__file__).parent / "data" / "unit_lahan_riil.json"
INDONESIA = (-11.5, 6.5, 94.5, 141.5)  # lat_min, lat_max, lon_min, lon_max

DRAINASE = ["baik", "agak baik", "agak cepat", "agak terhambat", "terhambat", "sangat terhambat", "cepat"]
TEKSTUR = ["sedang", "agak halus", "agak kasar", "halus", "sangat halus", "kasar"]


def _bangun_unit(kawasan, n):
    b = kawasan["bbox"]
    dlat = (b["lat_max"] - b["lat_min"]) / n
    dlon = (b["lon_max"] - b["lon_min"]) / n
    d = kawasan["dasar"]
    units = []
    for i in range(n):
        for j in range(n):
            rng = random.Random(f"{kawasan['id']}-{i}-{j}")
            lat0 = b["lat_min"] + i * dlat
            lon0 = b["lon_min"] + j * dlon
            nilai = {
                "suhu_rerata_c": round(rng.gauss(d["suhu_rerata_c"], 1.8), 1),
                "curah_hujan_mm": int(round(rng.gauss(d["curah_hujan_mm"], 300), -1)),
                "ph_tanah": round(rng.gauss(d["ph_tanah"], 0.35), 1),
                "c_organik_persen": round(max(0.3, rng.gauss(d["c_organik_persen"], 0.45)), 2),
                "lereng_persen": round(abs(rng.gauss(d["lereng_persen"], 6)), 1),
                "drainase": rng.choices(DRAINASE, weights=[40, 25, 10, 12, 7, 2, 4])[0],
                "tekstur": rng.choices(TEKSTUR, weights=[40, 25, 15, 12, 5, 3])[0],
            }
            if rng.random() < 0.08:  # sebagian petak belum punya data salah satu parameter
                nilai[rng.choice(["ph_tanah", "c_organik_persen", "tekstur"])] = None
            elevasi = int(round(rng.gauss(d["elevasi_m"], 120), -1))
            units.append({
                "id": f"{kawasan['id']}-{i}-{j}",
                "kawasan_id": kawasan["id"],
                "bbox": [lat0, lon0, lat0 + dlat, lon0 + dlon],
                "nilai": nilai,
                "elevasi_m": elevasi,
            })
    return units


def _muat_contoh():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    n = data["ukuran_grid"]
    kawasan = {k["id"]: k for k in data["kawasan"]}
    units = [u for k in data["kawasan"] for u in _bangun_unit(k, n)]
    return kawasan, units


def _muat_riil():
    with open(RIIL_PATH, encoding="utf-8") as f:
        data = json.load(f)
    # buang petak yang tumpang tindih dengan kawasan lain yang sudah dimuat (sentra berdekatan)
    units = []
    for u in data["units"]:
        la, lo = (u["bbox"][0] + u["bbox"][2]) / 2, (u["bbox"][1] + u["bbox"][3]) / 2
        if not any(v["bbox"][0] <= la < v["bbox"][2] and v["bbox"][1] <= lo < v["bbox"][3] for v in units):
            units.append(u)
    data["units"] = units
    kawasan = {}
    for k in data["kawasan"]:
        uk = [u for u in data["units"] if u["kawasan_id"] == k["id"]]
        if not uk:
            continue
        kawasan[k["id"]] = {**k, "bbox": {"lat_min": min(u["bbox"][0] for u in uk), "lat_max": max(u["bbox"][2] for u in uk),
                                          "lon_min": min(u["bbox"][1] for u in uk), "lon_max": max(u["bbox"][3] for u in uk)}}
    return kawasan, data["units"], data.get("sumber", {})


MODE = os.environ.get("DATA_MODE") or ("riil" if RIIL_PATH.exists() else "contoh")
if MODE == "riil":
    KAWASAN, UNITS, INFO_SUMBER = _muat_riil()
else:
    KAWASAN, UNITS = _muat_contoh()
    INFO_SUMBER = {"semua": "data contoh (dummy)"}

_cache = {}
_kunci = threading.Lock()


def _cache_get(key, fn):
    with _kunci:
        if key in _cache:
            return _cache[key]
    v = fn()
    with _kunci:
        _cache[key] = v
    return v


def _jarak_km(lat1, lon1, lat2, lon2):
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def cari_unit(lat, lon):
    """Unit lahan yang memuat titik (lat, lon), atau None bila tidak ada."""
    for u in UNITS:
        a, b, c, d = u["bbox"]
        if a <= lat < c and b <= lon < d:
            return u
    return None


def di_indonesia(lat, lon):
    a, b, c, d = INDONESIA
    return a <= lat <= b and c <= lon <= d


def sumber_parameter():
    """Nama sumber per parameter untuk ditampilkan di aplikasi."""
    if MODE != "riil":
        return None
    import sumber_riil
    return dict(sumber_riil.SUMBER)


def _nama(lat, lon):
    import sumber_riil
    return _cache_get(("nama", round(lat, 3), round(lon, 3)), lambda: sumber_riil.nama_tempat(lat, lon))


def data_lokasi(lat, lon):
    """Data otomatis untuk satu lokasi (dipakai layar Analisis Lahan). None = di luar cakupan."""
    u = cari_unit(lat, lon)
    if MODE != "riil":
        if u is None:
            return None
        k = KAWASAN[u["kawasan_id"]]
        desa = min(k["desa"], key=lambda x: _jarak_km(lat, lon, x["lat"], x["lon"]))
        return {"unit_id": u["id"], "asal": "contoh",
                "lokasi": {"lat": lat, "lon": lon, "desa": desa["nama"], "kecamatan": desa["kecamatan"],
                           "kabupaten": k["kabupaten"], "provinsi": k["provinsi"], "kawasan": k["nama"]},
                "elevasi_m": u["elevasi_m"], "nilai": dict(u["nilai"])}

    if u is not None:  # titik di dalam grid riil yang sudah dikumpulkan -> instan
        k = KAWASAN[u["kawasan_id"]]
        n = _nama(lat, lon)
        return {"unit_id": u["id"], "asal": "grid",
                "lokasi": {"lat": lat, "lon": lon, "desa": n["desa"], "kecamatan": n["kecamatan"],
                           "kabupaten": k["kabupaten"], "provinsi": k["provinsi"], "kawasan": k["nama"]},
                "elevasi_m": u["elevasi_m"], "nilai": dict(u["nilai"])}

    if not di_indonesia(lat, lon):
        return None
    import sumber_riil  # titik lain di Indonesia -> ambil langsung dari sumber riil (±5–10 dtk, lalu di-cache)
    d = _cache_get(("titik", round(lat, 3), round(lon, 3)), lambda: sumber_riil.data_titik(lat, lon))
    n = d["nama"]
    return {"unit_id": None, "asal": "langsung",
            "lokasi": {"lat": lat, "lon": lon, "desa": n["desa"], "kecamatan": n["kecamatan"],
                       "kabupaten": n["kabupaten"], "provinsi": n["provinsi"], "kawasan": None},
            "elevasi_m": d["elevasi_m"], "nilai": dict(d["nilai"]), "iklim_tahunan": d["tambahan"]["iklim_tahunan"]}


def cari_tempat(q, batas=8):
    """Pencarian kawasan sentra (lokal) + desa/kecamatan di seluruh Indonesia (Nominatim)."""
    q = q.strip().lower()
    hasil = []
    for k in KAWASAN.values():
        if MODE != "riil":
            for d in k["desa"]:
                teks = f"{d['nama']} {d['kecamatan']} {k['kabupaten']} {k['nama']}".lower()
                if q and q in teks:
                    hasil.append({"nama": d["nama"], "keterangan": f"Kec. {d['kecamatan']}, Kab. {k['kabupaten']}",
                                  "lat": d["lat"], "lon": d["lon"]})
        elif q and q in f"{k['nama']} {k['kabupaten']} {k['provinsi']}".lower():
            hasil.append({"nama": k["nama"], "keterangan": f"Sentra bawang putih, Kab. {k['kabupaten']}",
                          "lat": k["lat"], "lon": k["lon"]})
    if MODE == "riil" and len(hasil) < batas:
        import sumber_riil
        hasil += _cache_get(("cari", q), lambda: sumber_riil.cari_nama(q))
    return hasil[:batas]


def daftar_kawasan():
    return [{"id": k["id"], "nama": k["nama"], "kabupaten": k["kabupaten"], "provinsi": k.get("provinsi"), "bbox": k["bbox"],
             "pusat": [(k["bbox"]["lat_min"] + k["bbox"]["lat_max"]) / 2,
                       (k["bbox"]["lon_min"] + k["bbox"]["lon_max"]) / 2]}
            for k in KAWASAN.values()]

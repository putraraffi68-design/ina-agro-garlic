"""
Pengambil DATA RIIL dari sumber publik gratis (tanpa API key):

  Tanah   : SoilGrids 2.0 (ISRIC), layanan WCS maps.isric.org, resolusi 250 m
            pH H2O, karbon organik tanah (SOC), pasir, liat; kedalaman 0–30 cm
  Iklim   : ERA5 / ERA5-Land reanalisis (ECMWF) lewat Open-Meteo Historical API,
            suhu rerata harian & curah hujan harian -> rerata tahunan
  Elevasi : Copernicus DEM GLO-90 lewat Open-Meteo Elevation API -> elevasi & lereng
  Nama    : OpenStreetMap Nominatim (reverse geocoding desa/kecamatan/kabupaten)

Tekstur diturunkan dari % pasir & liat (segitiga tekstur USDA -> kelompok tekstur
juknis BBSDLP). Drainase TIDAK tersedia di sumber publik global, sehingga diestimasi
dari tekstur + lereng (ditandai "estimasi" di aplikasi).
"""
import io
import json
import math
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image

UA = "INA-Agro-GARLIC/1.0 (prototipe akademik)"
TIMEOUT = 60
LAPSE_RATE = 0.0065  # °C per meter

# variabel SoilGrids: (nama layer, faktor pembagi ke satuan target)
SOIL_VARS = {"phh2o": 10.0, "soc": 10.0, "sand": 10.0, "clay": 10.0}  # pH, g/kg, %, %
DEPTHS = [("0-5cm", 5), ("5-15cm", 10), ("15-30cm", 15)]  # bobot = tebal lapisan

SUMBER = {
    "suhu_rerata_c": "ERA5 (Open-Meteo)",
    "curah_hujan_mm": "ERA5 (Open-Meteo)",
    "ph_tanah": "SoilGrids (ISRIC)",
    "c_organik_persen": "SoilGrids (ISRIC)",
    "lereng_persen": "Copernicus DEM",
    "drainase": "estimasi",
    "tekstur": "SoilGrids (ISRIC)",
}


def _get(url, raw=False, retry=3):
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                data = r.read()
            return data if raw else json.loads(data)
        except Exception:
            if i == retry - 1:
                raise
            time.sleep(2 * (i + 1))


# ---------------- tanah (SoilGrids WCS) ----------------
def wcs_grid(var, depth, lat_min, lat_max, lon_min, lon_max, res=0.0025):
    """Unduh raster SoilGrids untuk satu kotak. Kembalikan (array, lon0, lat0, res)."""
    q = {
        "map": f"/map/{var}.map", "SERVICE": "WCS", "VERSION": "2.0.1", "REQUEST": "GetCoverage",
        "COVERAGEID": f"{var}_{depth}_mean", "FORMAT": "GEOTIFF_INT16",
        "SUBSETTINGCRS": "http://www.opengis.net/def/crs/EPSG/0/4326",
        "OUTPUTCRS": "http://www.opengis.net/def/crs/EPSG/0/4326",
    }
    url = ("https://maps.isric.org/mapserv?" + urllib.parse.urlencode(q)
           + f"&SUBSET=X({lon_min},{lon_max})&SUBSET=Y({lat_min},{lat_max})"
           + f"&RESOLUTION=X({res})&RESOLUTION=Y({res})")
    im = Image.open(io.BytesIO(_get(url, raw=True)))
    arr = np.array(im).astype(float)
    tie = im.tag_v2.get(33922)
    scale = im.tag_v2.get(33550)
    return arr, tie[3], tie[4], scale[0]


def sampel_grid(grid, lat, lon, jendela=1):
    """Rerata piksel valid (bukan 0/nodata) di sekitar titik."""
    arr, lon0, lat0, res = grid
    j = int((lon - lon0) / res)
    i = int((lat0 - lat) / res)
    blok = arr[max(0, i - jendela):i + jendela + 1, max(0, j - jendela):j + jendela + 1]
    v = blok[(blok > 0) & (blok < 32000)]
    return float(v.mean()) if v.size else None


def tanah_kotak(lat_min, lat_max, lon_min, lon_max, res=0.0025):
    """Unduh semua layer tanah untuk satu kotak -> dict (var, depth) -> grid."""
    tugas = [(v, d) for v in SOIL_VARS for d, _ in DEPTHS]
    with ThreadPoolExecutor(6) as ex:
        hasil = list(ex.map(lambda t: wcs_grid(t[0], t[1], lat_min, lat_max, lon_min, lon_max, res), tugas))
    return dict(zip(tugas, hasil))


def tanah_dari_grid(grids, lat, lon):
    out = {}
    for v, f in SOIL_VARS.items():
        num, den = 0.0, 0.0
        for d, w in DEPTHS:
            x = sampel_grid(grids[(v, d)], lat, lon)
            if x is not None:
                num += x / f * w
                den += w
        out[v] = round(num / den, 2) if den else None
    return {
        "ph_tanah": round(out["phh2o"], 1) if out["phh2o"] is not None else None,
        "c_organik_persen": round(out["soc"] / 10, 2) if out["soc"] is not None else None,  # g/kg -> %
        "pasir_persen": out["sand"],
        "liat_persen": out["clay"],
    }


def tanah_titik(lat, lon):
    d = 0.004
    grids = tanah_kotak(lat - d, lat + d, lon - d, lon + d)
    return tanah_dari_grid(grids, lat, lon)


def kelas_tekstur(pasir, liat):
    """% pasir & liat -> kelompok tekstur juknis (halus ... kasar)."""
    if pasir is None or liat is None:
        return None
    if liat >= 60:
        return "sangat halus"
    if liat >= 40:
        return "halus"
    if liat >= 27:
        return "agak halus"
    if pasir >= 70 and liat < 15:
        return "kasar"
    if pasir >= 52:
        return "agak kasar"
    return "sedang"


def estimasi_drainase(tekstur, lereng):
    """Perkiraan kelas drainase dari tekstur dan lereng (bukan data pengukuran)."""
    if tekstur is None:
        return None
    datar = lereng is not None and lereng < 3
    if tekstur == "kasar":
        return "cepat"
    if tekstur == "agak kasar":
        return "agak cepat"
    if tekstur == "sangat halus":
        return "terhambat" if datar else "agak terhambat"
    if tekstur == "halus" and datar:
        return "agak terhambat"
    return "baik"


# ---------------- elevasi & lereng (Copernicus DEM) ----------------
def elevasi(coords):
    """coords: list (lat, lon). Dibagi per 100 titik."""
    out = []
    for k in range(0, len(coords), 100):
        bag = coords[k:k + 100]
        url = ("https://api.open-meteo.com/v1/elevation?latitude=" + ",".join(f"{a:.5f}" for a, _ in bag)
               + "&longitude=" + ",".join(f"{b:.5f}" for _, b in bag))
        out += _get(url)["elevation"]
    return out


OFFSET_LERENG = 0.0009  # ≈100 m


def titik_lereng(lat, lon):
    d = OFFSET_LERENG
    return [(lat, lon), (lat + d, lon), (lat - d, lon), (lat, lon + d), (lat, lon - d)]


def hitung_lereng(lat, z):
    """z: elevasi [pusat, utara, selatan, timur, barat] -> (elevasi, lereng %)."""
    zc, zn, zs, ze, zw = z
    dy = 2 * OFFSET_LERENG * 111320
    dx = 2 * OFFSET_LERENG * 111320 * math.cos(math.radians(lat))
    gx, gy = (ze - zw) / dx, (zn - zs) / dy
    return zc, round(math.hypot(gx, gy) * 100, 1)


# ---------------- iklim (ERA5 via Open-Meteo) ----------------
def iklim_tahunan(coords, tahun_awal=2014, tahun_akhir=2023):
    """
    coords: list (lat, lon). Kembalikan per titik:
    {"elevasi_ref": m, "tahunan": {tahun: {"suhu": °C, "hujan": mm}}, "suhu": rerata, "hujan": rerata}
    """
    out = []
    for k in range(0, len(coords), 5):
        bag = coords[k:k + 5]
        url = ("https://archive-api.open-meteo.com/v1/archive?latitude=" + ",".join(f"{a:.4f}" for a, _ in bag)
               + "&longitude=" + ",".join(f"{b:.4f}" for _, b in bag)
               + f"&start_date={tahun_awal}-01-01&end_date={tahun_akhir}-12-31"
               + "&daily=temperature_2m_mean,precipitation_sum&timezone=Asia%2FJakarta")
        r = _get(url)
        if isinstance(r, dict):
            r = [r]
        for x in r:
            per = {}
            for t, s, h in zip(x["daily"]["time"], x["daily"]["temperature_2m_mean"], x["daily"]["precipitation_sum"]):
                y = int(t[:4])
                p = per.setdefault(y, {"s": [], "h": 0.0})
                if s is not None:
                    p["s"].append(s)
                if h is not None:
                    p["h"] += h
            tahunan = {y: {"suhu": round(sum(p["s"]) / len(p["s"]), 2), "hujan": round(p["h"])}
                       for y, p in per.items() if p["s"]}
            out.append({
                "elevasi_ref": x.get("elevation"),
                "tahunan": tahunan,
                "suhu": round(sum(v["suhu"] for v in tahunan.values()) / len(tahunan), 1),
                "hujan": int(round(sum(v["hujan"] for v in tahunan.values()) / len(tahunan), -1)),
            })
        time.sleep(1)
    return out


def koreksi_suhu(suhu_ref, elev_ref, elev_titik):
    """Koreksi suhu ke elevasi titik dengan lapse rate 0,65 °C/100 m."""
    if elev_ref is None or elev_titik is None:
        return suhu_ref
    return round(suhu_ref - LAPSE_RATE * (elev_titik - elev_ref), 1)


# ---------------- nama tempat (Nominatim) ----------------
def nama_tempat(lat, lon):
    try:
        r = _get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=14"
                 "&accept-language=id", retry=1)
        a = r.get("address", {})
        return {
            "desa": a.get("village") or a.get("town") or a.get("hamlet") or a.get("suburb") or "-",
            "kecamatan": a.get("city_district") or a.get("municipality") or a.get("district") or "-",
            "kabupaten": (a.get("county") or a.get("city") or "-").replace("Kabupaten ", ""),
            "provinsi": a.get("state", "-"),
        }
    except Exception:
        return {"desa": "-", "kecamatan": "-", "kabupaten": "-", "provinsi": "-"}


def cari_nama(q, batas=6):
    try:
        r = _get("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
            {"q": q, "format": "json", "countrycodes": "id", "limit": batas, "accept-language": "id"}), retry=1)
    except Exception:
        return []
    return [{"nama": x["display_name"].split(",")[0], "keterangan": ", ".join(x["display_name"].split(",")[1:3]).strip(),
             "lat": float(x["lat"]), "lon": float(x["lon"])} for x in r]


# ---------------- satu titik lengkap (analisis lokasi mana pun) ----------------
def data_titik(lat, lon):
    """Ambil 7 parameter riil untuk satu titik (dipakai bila titik di luar grid yang sudah dikumpulkan)."""
    with ThreadPoolExecutor(4) as ex:
        f_tanah = ex.submit(tanah_titik, lat, lon)
        f_elev = ex.submit(elevasi, titik_lereng(lat, lon))
        f_iklim = ex.submit(iklim_tahunan, [(lat, lon)])
        f_nama = ex.submit(nama_tempat, lat, lon)
        tanah, z, ikl, nama = f_tanah.result(), f_elev.result(), f_iklim.result()[0], f_nama.result()
    elev, lereng = hitung_lereng(lat, z)
    tekstur = kelas_tekstur(tanah["pasir_persen"], tanah["liat_persen"])
    return {
        "nilai": {
            "suhu_rerata_c": koreksi_suhu(ikl["suhu"], ikl["elevasi_ref"], elev),
            "curah_hujan_mm": ikl["hujan"],
            "ph_tanah": tanah["ph_tanah"],
            "c_organik_persen": tanah["c_organik_persen"],
            "lereng_persen": lereng,
            "drainase": estimasi_drainase(tekstur, lereng),
            "tekstur": tekstur,
        },
        "elevasi_m": round(elev),
        "tambahan": {"pasir_persen": tanah["pasir_persen"], "liat_persen": tanah["liat_persen"],
                     "iklim_tahunan": ikl["tahunan"]},
        "nama": nama,
    }

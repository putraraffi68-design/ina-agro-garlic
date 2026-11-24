"""
Membangun dataset unit lahan RIIL untuk sentra bawang putih.

Untuk tiap kawasan di app/data/sentra_bawang_putih.json:
  - grid 8x8 petak (jarak 0,02° ≈ 2,2 km)
  - tanah  : SoilGrids 2.0 (WCS) pH, SOC, pasir, liat 0–30 cm
  - elevasi & lereng : Copernicus DEM 90 m
  - iklim  : ERA5 2014–2023 di 3x3 titik acuan, dikoreksi ke elevasi petak (lapse rate)
Hasil:
  app/data/unit_lahan_riil.json       (dipakai peta & analisis)
  app/data/iklim_tahunan_kawasan.json (cuaca per tahun, untuk model prediksi panen)

Jalankan:  python scripts/kumpulkan_data_riil.py      (butuh internet, ±10–20 menit)
"""
import json
import sys
import time
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP))
import sumber_riil as sr  # noqa: E402

N, JARAK = 8, 0.02
REF = [-0.06, 0.0, 0.06]


def kumpulkan(k):
    t0 = time.time()
    lat_c, lon_c = k["lat"], k["lon"]
    awal = -(N - 1) / 2 * JARAK
    pusat = [(lat_c + awal + i * JARAK, lon_c + awal + j * JARAK) for i in range(N) for j in range(N)]
    m = N / 2 * JARAK + 0.01
    grids = sr.tanah_kotak(lat_c - m, lat_c + m, lon_c - m, lon_c + m)
    coords = [c for (a, b) in pusat for c in sr.titik_lereng(a, b)]
    z = sr.elevasi(coords)
    refs = [(lat_c + a, lon_c + b) for a in REF for b in REF]
    ikl = sr.iklim_tahunan(refs)
    units = []
    for idx, (a, b) in enumerate(pusat):
        elev, lereng = sr.hitung_lereng(a, z[idx * 5: idx * 5 + 5])
        t = sr.tanah_dari_grid(grids, a, b)
        r = min(range(len(refs)), key=lambda q: (refs[q][0] - a) ** 2 + (refs[q][1] - b) ** 2)
        tekstur = sr.kelas_tekstur(t["pasir_persen"], t["liat_persen"])
        darat = elev is not None and elev > 1 and t["ph_tanah"] is not None
        if not darat:
            continue  # laut / danau / tanpa data tanah
        units.append({
            "id": f"{k['id']}-{idx // N}-{idx % N}",
            "kawasan_id": k["id"],
            "bbox": [a - JARAK / 2, b - JARAK / 2, a + JARAK / 2, b + JARAK / 2],
            "nilai": {
                "suhu_rerata_c": sr.koreksi_suhu(ikl[r]["suhu"], ikl[r]["elevasi_ref"], elev),
                "curah_hujan_mm": ikl[r]["hujan"],
                "ph_tanah": t["ph_tanah"],
                "c_organik_persen": t["c_organik_persen"],
                "lereng_persen": lereng,
                "drainase": sr.estimasi_drainase(tekstur, lereng),
                "tekstur": tekstur,
            },
            "elevasi_m": round(elev),
            "pasir_persen": t["pasir_persen"],
            "liat_persen": t["liat_persen"],
        })
    tahun = sorted(ikl[0]["tahunan"])
    iklim_kaw = {y: {"suhu": round(sum(x["tahunan"][y]["suhu"] for x in ikl) / len(ikl), 2),
                     "hujan": round(sum(x["tahunan"][y]["hujan"] for x in ikl) / len(ikl))} for y in tahun}
    print(f"  {k['kabupaten']}: {len(units)} petak, {time.time() - t0:.0f} dtk", flush=True)
    return units, iklim_kaw


def main():
    sentra = json.load(open(APP / "data" / "sentra_bawang_putih.json", encoding="utf-8"))["kawasan"]
    semua, iklim = [], {}
    for k in sentra:
        print("Mengumpulkan", k["kabupaten"], "…", flush=True)
        u, ik = kumpulkan(k)
        semua += u
        iklim[k["id"]] = ik
    meta = {
        "_catatan": "Data riil hasil scripts/kumpulkan_data_riil.py",
        "dibuat": time.strftime("%Y-%m-%d"),
        "sumber": {"tanah": "SoilGrids 2.0 (ISRIC), 250 m, 0–30 cm", "iklim": "ERA5/ERA5-Land via Open-Meteo, rerata 2014–2023",
                   "elevasi": "Copernicus DEM GLO-90", "drainase": "estimasi dari tekstur & lereng"},
        "ukuran_petak_derajat": JARAK,
        "kawasan": sentra,
        "units": semua,
    }
    json.dump(meta, open(APP / "data" / "unit_lahan_riil.json", "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(iklim, open(APP / "data" / "iklim_tahunan_kawasan.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Selesai: {len(semua)} unit lahan riil dari {len(sentra)} kawasan.")


if __name__ == "__main__":
    main()

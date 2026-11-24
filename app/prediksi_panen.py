"""
Fitur ML: prediksi hasil panen (produktivitas) bawang putih, ton/ha.

Data latih
  Target  : produktivitas riil = produksi (ton) / luas panen (ha) per kabupaten per tahun,
            dari BPS (data/produktivitas_bps.csv, dibuat oleh scripts/ambil_data_bps.py)
  Fitur   : cuaca tahun itu (ERA5: suhu rerata, curah hujan) di sentra kabupaten tsb.
            + karakteristik lahan sentra (median grid riil: pH, C-organik, lereng, elevasi)
Model     : Random Forest Regressor (scikit-learn)
Evaluasi  : dua skenario, masing-masing dibandingkan baseline "pakai rata-rata saja":
            - leave-one-year-out   : menebak tahun yang tidak dilihat di kabupaten yang sudah dikenal
            - leave-one-kabupaten-out : menebak kabupaten yang tidak pernah dilihat (lokasi baru)
Prediksi  : untuk satu lokasi, fitur diambil dari data lokasi tsb (iklim rerata 10 tahun),
            hasil = median prediksi pohon, rentang = persentil 10–90 antar pohon.

Latih ulang:  python scripts/latih_model_panen.py
"""
import csv
import json
import statistics
from pathlib import Path

import numpy as np

DATA = Path(__file__).parent / "data"
MODEL_PATH = DATA / "model_panen.joblib"
INFO_PATH = DATA / "model_panen_info.json"
FITUR = ["suhu_rerata_c", "curah_hujan_mm", "ph_tanah", "c_organik_persen", "lereng_persen", "elevasi_m"]
LABEL_FITUR = {"suhu_rerata_c": "Suhu rerata", "curah_hujan_mm": "Curah hujan", "ph_tanah": "pH tanah",
               "c_organik_persen": "C-organik", "lereng_persen": "Lereng", "elevasi_m": "Elevasi"}


def bangun_dataset():
    """Gabungkan data BPS + iklim tahunan + lahan sentra -> (X, y, grup, baris)."""
    sentra = json.load(open(DATA / "unit_lahan_riil.json", encoding="utf-8"))
    iklim = json.load(open(DATA / "iklim_tahunan_kawasan.json", encoding="utf-8"))
    lahan = {}
    for k in sentra["kawasan"]:
        uk = [u for u in sentra["units"] if u["kawasan_id"] == k["id"]]
        if not uk:
            continue
        med = lambda f: statistics.median(u["nilai"][f] if f in u["nilai"] else u[f] for u in uk
                                          if (u["nilai"].get(f) if f in u["nilai"] else u.get(f)) is not None)
        lahan[k["id"]] = {f: med(f) for f in ["ph_tanah", "c_organik_persen", "lereng_persen", "elevasi_m"]}
        lahan[k["id"]]["suhu_dasar"] = med("suhu_rerata_c")
        lahan[k["id"]]["kabupaten"] = k["kabupaten"]
    X, y, grup, baris = [], [], [], []
    with open(DATA / "produktivitas_bps.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            kid, th = r["kawasan_id"], str(r["tahun"])
            if kid not in lahan or th not in iklim.get(kid, {}):
                continue
            prod, luas = float(r["produksi_ton"] or 0), float(r["luas_panen_ha"] or 0)
            if prod <= 0 or luas <= 0:
                continue
            ik = iklim[kid][th]
            # suhu kawasan tahun itu, disesuaikan ke elevasi median sentra (anomali tahun + suhu dasar)
            rerata_suhu = sum(v["suhu"] for v in iklim[kid].values()) / len(iklim[kid])
            suhu = lahan[kid]["suhu_dasar"] + (ik["suhu"] - rerata_suhu)
            fitur = {"suhu_rerata_c": suhu, "curah_hujan_mm": ik["hujan"], **{k: lahan[kid][k] for k in
                     ["ph_tanah", "c_organik_persen", "lereng_persen", "elevasi_m"]}}
            X.append([fitur[f] for f in FITUR])
            y.append(prod / luas)
            grup.append(kid)
            baris.append({"kawasan_id": kid, "kabupaten": lahan[kid]["kabupaten"], "tahun": int(th),
                          "produktivitas_ton_ha": round(prod / luas, 2), **{f: round(fitur[f], 2) for f in FITUR}})
    return np.array(X), np.array(y), np.array(grup), baris


def latih(n_pohon=300, seed=42):
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
    import joblib

    X, y, grup, baris = bangun_dataset()
    if len(y) < 10:
        raise SystemExit(f"Data latih terlalu sedikit ({len(y)} baris).")
    tahun = np.array([b["tahun"] for b in baris])

    def uji_silang(kelompok):
        pred, base = np.zeros_like(y), np.zeros_like(y)
        for g in np.unique(kelompok):
            uji = kelompok == g
            m = RandomForestRegressor(n_estimators=n_pohon, min_samples_leaf=5, random_state=seed)
            m.fit(X[~uji], y[~uji])
            pred[uji] = m.predict(X[uji])
            base[uji] = y[~uji].mean()
        return {"mae_ton_ha": round(float(mean_absolute_error(y, pred)), 2),
                "mae_baseline_ton_ha": round(float(mean_absolute_error(y, base)), 2),
                "r2": round(float(r2_score(y, pred)), 2)}

    ev_tahun, ev_kab = uji_silang(tahun), uji_silang(grup)
    model = RandomForestRegressor(n_estimators=n_pohon, min_samples_leaf=5, random_state=seed).fit(X, y)
    joblib.dump(model, MODEL_PATH)
    info = {
        "model": "RandomForestRegressor",
        "jumlah_data": int(len(y)),
        "jumlah_kabupaten": int(len(np.unique(grup))),
        "tahun": [int(min(b["tahun"] for b in baris)), int(max(b["tahun"] for b in baris))],
        "fitur": FITUR,
        "kabupaten_latih": sorted({b["kawasan_id"] for b in baris}),
        "evaluasi_tahun_baru": ev_tahun,
        "evaluasi_kabupaten_baru": ev_kab,
        "mae_ton_ha": ev_tahun["mae_ton_ha"],
        "rerata_produktivitas_ton_ha": round(float(y.mean()), 2),
        "kepentingan_fitur": {LABEL_FITUR[f]: round(float(v), 3) for f, v in
                              sorted(zip(FITUR, model.feature_importances_), key=lambda t: -t[1])},
        "sumber_target": "BPS: produksi & luas panen bawang putih per kabupaten",
    }
    json.dump(info, open(INFO_PATH, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    with open(DATA / "dataset_latih_panen.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(baris[0].keys()))
        w.writeheader()
        w.writerows(baris)
    return info


_model = None


def info_model():
    return json.load(open(INFO_PATH, encoding="utf-8")) if INFO_PATH.exists() else None


def prediksi(nilai, elevasi_m, kawasan_id=None):
    """nilai: 7 parameter lokasi. Kembalikan dict prediksi atau None bila model/fitur tidak tersedia."""
    global _model
    if not MODEL_PATH.exists():
        return None
    fitur = {**nilai, "elevasi_m": elevasi_m}
    if any(fitur.get(f) is None for f in FITUR):
        return None
    if _model is None:
        import joblib
        _model = joblib.load(MODEL_PATH)
    x = np.array([[float(fitur[f]) for f in FITUR]])
    per_pohon = np.array([t.predict(x)[0] for t in _model.estimators_])
    info = info_model() or {}
    dikenal = kawasan_id in info.get("kabupaten_latih", [])
    return {
        "dalam_data_latih": dikenal,
        "ton_per_ha": round(float(np.median(per_pohon)), 1),
        "rentang_ton_per_ha": [round(float(np.percentile(per_pohon, 10)), 1), round(float(np.percentile(per_pohon, 90)), 1)],
        "rerata_sentra_ton_per_ha": info.get("rerata_produktivitas_ton_ha"),
        "mae_ton_per_ha": (info.get("evaluasi_tahun_baru") if dikenal else info.get("evaluasi_kabupaten_baru", {})).get("mae_ton_ha"),
        "model": "Random Forest",
        "catatan": "Perkiraan dari pola produktivitas kabupaten sentra (BPS) terhadap iklim dan lahan; "
                   "hasil nyata sangat dipengaruhi varietas, benih, dan budidaya.",
    }

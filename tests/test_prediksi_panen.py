"""Uji fitur ML prediksi hasil panen (memakai model & data yang sudah ada di app/data)."""
import prediksi_panen as pp


def test_dataset_bps_riil():
    X, y, grup, baris = pp.bangun_dataset()
    assert len(y) >= 50 and len(set(grup)) >= 5
    assert 2 < y.mean() < 15  # produktivitas bawang putih wajar (ton/ha)


def test_prediksi_lokasi_dikenal():
    nilai = {"suhu_rerata_c": 19, "curah_hujan_mm": 2900, "ph_tanah": 5.4, "c_organik_persen": 6.0,
             "lereng_persen": 15, "drainase": "baik", "tekstur": "agak halus"}
    p = pp.prediksi(nilai, 1400, "temanggung")
    assert p and p["dalam_data_latih"] and p["rentang_ton_per_ha"][0] <= p["ton_per_ha"] <= p["rentang_ton_per_ha"][1]
    assert not pp.prediksi(nilai, 1400, None)["dalam_data_latih"]
    assert pp.prediksi({**nilai, "ph_tanah": None}, 1400) is None


def test_info_model():
    i = pp.info_model()
    assert i["evaluasi_tahun_baru"]["mae_ton_ha"] > 0 and "kepentingan_fitur" in i

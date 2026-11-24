"""Uji fungsional rule engine: 20 kasus berlabel dari PoC LKP 6 (harus 20/20)."""
import pytest
from rule_engine import klasifikasi, kelas_parameter, dekat_ambang
from rekomendasi import buat_rekomendasi

P = ["suhu_rerata_c", "curah_hujan_mm", "ph_tanah", "c_organik_persen",
     "lereng_persen", "drainase", "tekstur"]
KASUS = [
    ((18, 1500, 6.2, 2.0, 5, "baik", "sedang"), "S1"),
    ((20, 1800, 6.8, 1.5, 3, "agak baik", "agak halus"), "S1"),
    ((16, 1200, 5.8, 1.3, 7, "baik", "sedang"), "S1"),
    ((23, 1500, 6.2, 2.0, 5, "baik", "sedang"), "S2"),
    ((18, 2200, 6.0, 2.0, 5, "baik", "sedang"), "S2"),
    ((18, 1500, 5.3, 2.0, 5, "baik", "sedang"), "S2"),
    ((18, 1500, 6.2, 1.0, 5, "baik", "sedang"), "S2"),
    ((18, 1500, 6.2, 2.0, 12, "baik", "sedang"), "S2"),
    ((18, 1500, 6.2, 2.0, 5, "agak terhambat", "sedang"), "S2"),
    ((18, 1500, 6.2, 2.0, 5, "baik", "halus"), "S2"),
    ((26, 1500, 6.2, 2.0, 5, "baik", "sedang"), "S3"),
    ((18, 2700, 6.2, 2.0, 5, "baik", "sedang"), "S3"),
    ((18, 1500, 4.8, 2.0, 5, "baik", "sedang"), "S3"),
    ((18, 1500, 6.2, 2.0, 20, "baik", "sedang"), "S3"),
    ((22, 2100, 5.4, 0.6, 10, "terhambat", "sedang"), "S3"),
    ((29, 1500, 6.2, 2.0, 5, "baik", "sedang"), "N"),
    ((18, 3200, 6.2, 2.0, 5, "baik", "sedang"), "N"),
    ((18, 1500, 4.2, 2.0, 5, "baik", "sedang"), "N"),
    ((18, 1500, 6.2, 2.0, 35, "baik", "sedang"), "N"),
    ((18, 1500, 6.2, 2.0, 5, "baik", "kasar"), "N"),
]


@pytest.mark.parametrize("nilai,label", KASUS)
def test_kasus_poc(nilai, label):
    assert klasifikasi(dict(zip(P, nilai)))["kelas_akhir"] == label


def test_faktor_pembatas_dan_penjelasan():
    h = klasifikasi(dict(zip(P, (18, 1500, 5.3, 2.0, 12, "baik", "sedang"))))
    assert h["kelas_akhir"] == "S2"
    assert h["faktor_pembatas"] == ["pH tanah", "kemiringan lereng"]
    assert h["penjelasan"].startswith("S2 karena pH tanah 5,3")
    assert h["kelengkapan_data"] == "7/7"


def test_data_hilang():
    u = dict(zip(P, (18, 1500, None, 2.0, 5, "baik", "sedang")))
    h = klasifikasi(u)
    assert h["kelengkapan_data"] == "6/7"
    assert h["parameter_hilang"] == ["pH tanah"]
    assert h["perlu_verifikasi_lapangan"]


def test_dekat_ambang():
    assert dekat_ambang("ph_tanah", 5.6)
    assert not dekat_ambang("ph_tanah", 6.3)
    assert kelas_parameter("drainase", "Baik ") == "S1"


def test_rekomendasi_pengapuran_dan_teras():
    h = klasifikasi(dict(zip(P, (18, 1500, 5.3, 2.0, 12, "baik", "sedang"))))
    rek = " ".join(buat_rekomendasi(h))
    assert "dolomit" in rek and "terasering" in rek and "Pupuk dasar" in rek

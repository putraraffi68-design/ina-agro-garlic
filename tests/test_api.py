"""Uji endpoint sesuai kontrak API LKP 6."""
from fastapi.testclient import TestClient
import main

c = TestClient(main.app)
KLEDUNG = {"lat": -7.334, "lon": 110.036}


def test_consent_wajib():
    r = c.post("/api/v1/analisis", json={**KLEDUNG, "consent": False})
    assert r.status_code == 422 and r.json()["detail"]["error"] == "consent belum diberikan"


def test_di_luar_cakupan():
    r = c.post("/api/v1/analisis", json={"lat": -6.2, "lon": 106.8, "consent": True})
    assert r.status_code == 400 and "cakupan" in r.json()["detail"]["error"]


def test_analisis_sesuai_kontrak():
    r = c.post("/api/v1/analisis", json={**KLEDUNG, "consent": True, "parameter_manual": {"ph_tanah": 5.3}})
    assert r.status_code == 200
    h = r.json()
    for k in ["analysis_id", "lokasi", "kelas_akhir", "label", "kelas_per_parameter", "faktor_pembatas",
              "penjelasan", "rekomendasi", "kelengkapan_data", "perlu_verifikasi_lapangan", "waktu_proses_ms"]:
        assert k in h
    assert h["kelas_per_parameter"]["ph_tanah"] == {**h["kelas_per_parameter"]["ph_tanah"], "nilai": 5.3, "sumber": "manual", "kelas": "S2"}
    assert h["lokasi"]["kabupaten"] == "Temanggung"
    assert h["waktu_proses_ms"] < 5000
    pdf = c.get(f"/api/v1/analisis/{h['analysis_id']}/pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_akun_simpan_riwayat_dan_cabut_consent():
    r = c.post("/api/v1/auth/daftar", json={"nama": "Uji", "kontak": "uji@contoh.id", "sandi": "rahasia1", "consent": True})
    assert r.status_code == 200
    H = {"Authorization": "Bearer " + r.json()["token"]}
    h = c.post("/api/v1/analisis", json={**KLEDUNG, "consent": True}, headers=H).json()
    assert c.post(f"/api/v1/riwayat/{h['analysis_id']}", headers=H).status_code == 200
    assert [x["analysis_id"] for x in c.get("/api/v1/riwayat", headers=H).json()] == [h["analysis_id"]]
    c.put("/api/v1/akun/consent", json={"consent": False}, headers=H)
    assert c.post("/api/v1/analisis", json={**KLEDUNG, "consent": True}, headers=H).status_code == 422
    assert c.post("/api/v1/auth/masuk", json={"kontak": "uji@contoh.id", "sandi": "salah"}).status_code == 401


def test_peta_dan_cari():
    assert len(c.get("/api/v1/peta-kesesuaian").json()) == 3 * 36
    assert c.get("/api/v1/cari", params={"q": "sembalun"}).json()[0]["nama"].startswith("Sembalun")

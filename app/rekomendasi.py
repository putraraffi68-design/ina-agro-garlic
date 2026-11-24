"""
Aturan rekomendasi budidaya & pupuk berdasarkan kelas akhir dan faktor pembatas (F4).
Angka dosis adalah ACUAN UMUM untuk prototipe; sesuaikan dengan hasil uji tanah
dan anjuran penyuluh/BPTP setempat.
"""
from rule_engine import arah_penyimpangan

# (parameter, arah) -> rekomendasi
ATURAN = {
    ("ph_tanah", "rendah"): lambda v: (
        "Pengapuran dolomit sekitar " + ("2–3" if v < 5.0 else "1–2") +
        " t/ha, disebar 2–4 minggu sebelum tanam (tanah masam)"),
    ("ph_tanah", "tinggi"): lambda v: (
        "Tanah agak basa: tambahkan bahan organik matang/belerang, hindari kapur dan pupuk bereaksi basa"),
    ("suhu_rerata_c", "tinggi"): lambda v: (
        "Suhu terlalu panas untuk bawang putih dataran tinggi: pilih varietas adaptif dataran "
        "medium (mis. Lumbu Putih) atau tanam di musim kemarau yang lebih sejuk"),
    ("suhu_rerata_c", "rendah"): lambda v: (
        "Suhu terlalu dingin: geser jadwal tanam ke bulan yang lebih hangat dan pantau risiko embun beku"),
    ("curah_hujan_mm", "tinggi"): lambda v: (
        "Curah hujan tinggi: tanam menjelang akhir musim hujan, buat bedengan tinggi dan saluran "
        "drainase, waspadai penyakit jamur (fungisida preventif)"),
    ("curah_hujan_mm", "rendah"): lambda v: (
        "Curah hujan kurang: siapkan irigasi (sumur/embung/irigasi tetes) dan mulsa jerami"),
    ("c_organik_persen", "rendah"): lambda v: (
        "C-organik rendah: tambahkan pupuk kandang/kompos matang 15–20 t/ha saat olah tanah"),
    ("lereng_persen", "tinggi"): lambda v: (
        "Lereng " + f"{v:g}".replace(".", ",") + "%: buat terasering/bedengan searah kontur dan "
        "tanaman penguat teras untuk mencegah erosi" + (" (lereng >30% tidak dianjurkan)" if v >= 30 else "")),
    ("drainase", "agak terhambat"): lambda v: "Drainase agak terhambat: bedengan tinggi 30–40 cm dan parit keliling",
    ("drainase", "terhambat"): lambda v: "Drainase terhambat: bedengan tinggi, parit dalam, hindari tanam di musim hujan",
    ("drainase", "sangat terhambat"): lambda v: "Drainase sangat terhambat: lahan tergenang, tidak dianjurkan untuk bawang putih",
    ("drainase", "agak cepat"): lambda v: "Drainase agak cepat: mulsa dan penambahan bahan organik untuk menahan air",
    ("drainase", "cepat"): lambda v: "Drainase terlalu cepat: tanah tidak menahan air, perlu irigasi rutin dan bahan organik tinggi",
    ("tekstur", "agak kasar"): lambda v: "Tekstur agak kasar (berpasir): tambah bahan organik dan berikan pupuk secara bertahap",
    ("tekstur", "halus"): lambda v: "Tekstur halus (liat): olah tanah lebih gembur, tambah bahan organik dan pasir halus",
    ("tekstur", "sangat halus"): lambda v: "Tekstur sangat halus: perbaikan struktur tanah intensif (bahan organik, bedengan tinggi)",
    ("tekstur", "kasar"): lambda v: "Tekstur kasar: daya simpan air & hara sangat rendah, tidak dianjurkan tanpa perbaikan besar",
}

PUPUK = {
    "S1": "Pupuk dasar: pupuk kandang 15 t/ha + N 150 kg/ha, P2O5 100 kg/ha, K2O 100 kg/ha (sesuaikan uji tanah)",
    "S2": "Pupuk dasar: pupuk kandang 20 t/ha + N 175 kg/ha, P2O5 120 kg/ha, K2O 120 kg/ha (sesuaikan uji tanah)",
    "S3": "Pupuk dasar: pupuk kandang 20–25 t/ha + N 200 kg/ha, P2O5 150 kg/ha, K2O 150 kg/ha; hitung dulu kelayakan biayanya",
    "N": "Lahan tidak dianjurkan untuk bawang putih; pertimbangkan komoditas lain yang lebih sesuai",
}


def buat_rekomendasi(hasil):
    """hasil: output rule_engine.klasifikasi(). Mengembalikan daftar teks rekomendasi."""
    rek = []
    # rekomendasi untuk SEMUA parameter yang tidak S1 (faktor pembatas dulu)
    urut = hasil["faktor_pembatas_kode"] + [
        k for k, d in hasil["kelas_per_parameter"].items()
        if d["kelas"] != "S1" and k not in hasil["faktor_pembatas_kode"]]
    for k in urut:
        nilai = hasil["kelas_per_parameter"][k]["nilai"]
        arah = arah_penyimpangan(k, nilai)
        fn = ATURAN.get((k, arah))
        if fn:
            rek.append(fn(nilai))
    rek.append(PUPUK[hasil["kelas_akhir"]])
    if hasil["perlu_verifikasi_lapangan"]:
        rek.append("Lakukan uji tanah dan verifikasi lapangan bersama penyuluh sebelum tanam")
    return rek

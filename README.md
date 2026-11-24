# INA Agro-GARLIC — Aplikasi Kesesuaian Lahan Bawang Putih

Prototipe yang bisa dijalankan, dibangun dari LKP 5–6 Kelompok 2: sistem pakar *rule-based*
(FAO 1976 / juknis BBSDLP, disederhanakan) yang menentukan kelas kesesuaian lahan **S1 / S2 / S3 / N**,
menunjukkan **faktor pembatas**, dan memberi **rekomendasi budidaya & pupuk**.

Bentuknya **aplikasi web** untuk dibuka di browser laptop/PC, dengan header navigasi 4 menu
(Beranda, Analisis Lahan, Peta Kesesuaian, Akun & Riwayat) sesuai IA di LKP 5. Isi dan alur layar
mengikuti wireframe LKP 6: **Login/Persetujuan → Analisis Lahan → Hasil Kesesuaian**, tetapi
ditata ulang dalam tata letak lebar (peta besar di kiri, panel data/hasil di kanan). Di layar
sempit kolom otomatis ditumpuk.

## Cara menjalankan

Butuh Python 3.10 atau lebih baru.

```bash
cd software
pip install -r requirements.txt
./jalankan.sh            # Windows: jalankan.bat
```

Lalu buka **http://localhost:8000** di browser.

Dokumentasi API otomatis (Swagger): **http://localhost:8000/docs**

Menjalankan pengujian:

```bash
cd software
python -m pytest -q tests
```

Hasil saat dibuat: **29 tes lulus**, termasuk 20 kasus berlabel dari PoC (20/20) dan uji kontrak API.

## Cara mencoba

1. Di halaman login, centang persetujuan lokasi lalu pilih **Coba tanpa akun (mode tamu)**,
   atau **Daftar akun baru** supaya bisa menyimpan riwayat.
2. Di **Analisis**, cari `Kledung`, `Sembalun`, atau `Tawangmangu` (atau ketik koordinat seperti
   `-7.33, 110.04`), klik peta, atau tekan **Lokasi saya**.
3. Periksa tabel **Data otomatis lokasi ini**. Kalau punya hasil uji tanah sendiri, tekan
   **Ubah manual** dan isi nilainya.
4. Klik **Analisis Kesesuaian** untuk melihat kelas, faktor pembatas, rekomendasi, mini peta,
   lalu **Simpan** atau **Unduh PDF**.
5. Menu **Peta Kesesuaian** menampilkan petak-petak unit lahan yang diwarnai menurut kelasnya.

## Data riil (baru)

Aplikasi sekarang memakai **data riil** secara bawaan (`DATA_MODE=riil`):

| Parameter | Sumber | Keterangan |
|---|---|---|
| pH, C-organik, tekstur (pasir/liat) | SoilGrids 2.0, ISRIC | 250 m, rata-rata 0–30 cm |
| Suhu rerata, curah hujan | ERA5/ERA5-Land via Open-Meteo | rerata tahunan 2014–2023 |
| Elevasi & lereng | Copernicus DEM GLO-90 via Open-Meteo | lereng dihitung dari elevasi ±100 m |
| Drainase | estimasi dari tekstur & lereng | tidak ada data publik; ditandai "estimasi" |
| Nama desa/kabupaten | OpenStreetMap Nominatim | |

- `app/data/unit_lahan_riil.json` berisi 686 unit lahan (petak ±2 km) di 11 sentra bawang putih,
  dibuat dengan `python scripts/kumpulkan_data_riil.py` (butuh internet, ±5 menit).
- Titik lain di Indonesia diambil langsung saat dianalisis (±4–7 detik, lalu di-cache).
- Mode lama (data contoh, tanpa internet): jalankan dengan `DATA_MODE=contoh`.
- **Temuan:** dengan kriteria PoC, sebagian besar lahan sentra jatuh ke kelas N karena curah hujan
  tahunan 2.500–4.600 mm. Kriteria curah hujan perlu diganti ke curah hujan masa tanam sesuai juknis BBSDLP.

## Prediksi hasil panen (ML)

`app/prediksi_panen.py`: model **Random Forest** yang memperkirakan produktivitas (ton/ha).

- **Data latih riil:** produksi dan luas panen bawang putih dari WebAPI BPS untuk Temanggung, Wonosobo,
  Magelang, Karanganyar, Tegal (2014–2023), dan Humbang Hasundutan (2019–2021). Totalnya 53 data
  (`app/data/produktivitas_bps.csv`), dengan rata-rata 7,0 ton/ha.
- **Fitur:** suhu dan curah hujan tahun tersebut (ERA5), ditambah pH, C-organik, lereng, dan elevasi sentra.
- **Hasil evaluasi (MAE):**
  - Tahun baru di kabupaten yang sudah dikenal: **1,57 ton/ha**, lebih baik dari baseline rata-rata (1,82).
  - Kabupaten baru: 2,32 ton/ha, **lebih buruk** dari baseline (1,95).

  Artinya model berguna untuk sentra yang datanya ada, tetapi belum untuk lokasi baru. Aplikasi menandai hal ini.
- **Mengambil ulang data dan melatih ulang:**
  1. `BPS_API_KEY=xxxx python scripts/ambil_data_bps.py`
  2. `python scripts/latih_model_panen.py`

  API key BPS tidak disimpan di kode.

## Web publik

Lihat **PANDUAN_DEPLOY.md** (Render, gratis, tanpa terminal).

## Fitur yang sudah jalan (dipetakan ke SRS LKP 5)

| Fitur | Status |
|---|---|
| F1 Input lokasi: pencarian desa/koordinat, peta interaktif, pin bisa digeser, GPS | ✅ |
| F2 Klasifikasi kesesuaian (rule engine PoC), faktor pembatas, penjelasan | ✅ |
| F3 Peta kawasan berwarna per kelas | ✅ |
| F4 Rekomendasi budidaya & dosis pupuk per faktor pembatas dan kelas | ✅ (dosis acuan umum) |
| F5 Riwayat analisis & unduh laporan PDF | ✅ |
| Akun, mode tamu, persetujuan (opt-in) lokasi yang bisa dicabut | ✅ |
| Indikator kepastian: kelengkapan data, nilai dekat ambang, saran verifikasi lapangan | ✅ |
| Respons < 5 detik | ✅ (analisis < 5 ms di server) |

## Struktur

```
software/
├── app/
│   ├── main.py                 # FastAPI: endpoint API + menyajikan frontend
│   ├── rule_engine.py          # logika PoC (hukum minimum) yang dirapikan jadi modul
│   ├── rekomendasi.py          # aturan rekomendasi budidaya & pupuk (F4)
│   ├── data_spasial.py         # "lokasi ini masuk unit lahan mana" (pengganti PostGIS)
│   ├── db.py                   # SQLite: akun, sesi, consent, riwayat (pengganti PostgreSQL)
│   ├── laporan_pdf.py          # laporan PDF (reportlab)
│   ├── data/
│   │   ├── kriteria_bawang_putih.json   # tabel kriteria, bisa diubah pakar tanpa ubah kode
│   │   └── kawasan_dummy.json           # 3 kawasan contoh + daftar desa
│   └── static/                 # frontend: index.html, app.js, style.css, Leaflet (offline)
├── tests/                      # pytest: 20 kasus PoC + uji API
├── docs/                       # tangkapan layar
├── requirements.txt
└── jalankan.sh / jalankan.bat
```

## Kontrak API (sesuai LKP 6)

`POST /api/v1/analisis`

```json
{ "lat": -7.334, "lon": 110.036, "consent": true, "parameter_manual": { "ph_tanah": 5.3 } }
```

Balasan berisi `analysis_id`, `lokasi`, `kelas_akhir`, `label`, `kelas_per_parameter`
(nilai, ideal, kelas, sumber, dekat_ambang), `faktor_pembatas`, `penjelasan`, `rekomendasi`,
`kelengkapan_data`, `perlu_verifikasi_lapangan`, `waktu_proses_ms`.
Error: `400 lokasi di luar kawasan cakupan MVP`, `422 consent belum diberikan`.

Endpoint lain: `GET /api/v1/data-lokasi`, `GET /api/v1/cari`, `GET /api/v1/kawasan`,
`GET /api/v1/peta-kesesuaian`, `GET /api/v1/kriteria`, `GET /api/v1/analisis/{id}/pdf`,
`POST|GET|DELETE /api/v1/riwayat`, `POST /api/v1/auth/daftar|masuk|keluar`, `PUT /api/v1/akun/consent`.

## Batasan prototipe (penting untuk laporan)

- **Data spasial masih data contoh.** Tiga kawasan (Kledung–Bansari Temanggung, Sembalun
  Lombok Timur, Tawangmangu Karanganyar) dibagi jadi 6×6 petak dengan nilai yang dibangkitkan dari
  nilai dasar kawasan. Ganti dengan data BMKG, peta tanah BBSDLP, dan DEM (tugas no. 3) dengan
  mengganti `data_spasial.cari_unit` menjadi query PostGIS; API dan rule engine tidak perlu diubah.
- **Ambang kriteria belum dikalibrasi pakar.** Sama dengan PoC; ubah di `kriteria_bawang_putih.json`.
- **Dosis pupuk/kapur adalah acuan umum**, bukan rekomendasi resmi.
- Peta dasar memakai tile OpenStreetMap, jadi butuh internet. Leaflet sudah disertakan offline.
- Stack disederhanakan dari blueprint LKP 6 supaya bisa jalan dengan satu perintah: frontend
  memakai JavaScript biasa (bukan React) dan database SQLite (bukan PostgreSQL+PostGIS). Backend
  FastAPI dan rule engine Python sudah sesuai blueprint, sehingga frontend React nanti tinggal
  memanggil API yang sama.

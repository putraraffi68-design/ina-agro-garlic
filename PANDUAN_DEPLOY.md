# Panduan Membuat INA Agro-GARLIC Jadi Web Publik (gratis, tanpa terminal)

Hasil akhirnya adalah link seperti `https://ina-agro-garlic.onrender.com` yang bisa dibuka siapa saja.
Kita memakai dua layanan gratis:

- **GitHub**, tempat menyimpan kode.
- **Render**, server yang menjalankan aplikasinya. Paket gratisnya cukup untuk prototipe.

Total waktu sekitar 20–30 menit. Semua langkah dilakukan lewat browser.

---

## Bagian A — Simpan kode di GitHub

1. Buka **https://github.com/signup** dan buat akun. Kalau sudah punya akun, langsung login.
2. Setelah login, klik tombol **+** di kanan atas, lalu pilih **New repository**.
3. Isi formnya:
   - **Repository name:** `ina-agro-garlic`
   - Pilih **Public** (atau Private, keduanya bisa).
   - **Jangan** centang "Add a README".
   - Klik **Create repository**.
4. Masukkan kodenya ke repository. Pilih **salah satu** cara berikut:

   **Cara 1 (paling mudah): biarkan Claude yang mengunggah.**
   1. Buka **https://claude.ai/connect-github** dan hubungkan akun GitHub-mu.
   2. Pasang **Claude GitHub App** di https://github.com/apps/claude/installations/select_target, lalu pilih repository `ina-agro-garlic`.
   3. Kabari Claude di thread ini: "repo sudah siap: github.com/NAMA-AKUNMU/ina-agro-garlic". Claude akan mengunggah semua kodenya.

   **Cara 2: unggah sendiri lewat browser.**
   1. Ekstrak file `software_ina_agro_garlic.zip` di laptop.
   2. Di halaman repository yang masih kosong, klik link **uploading an existing file**.
   3. Buka folder hasil ekstrak, masuk ke folder `software`, pilih **semua isinya** (folder `app`, `scripts`, `tests`, `docs`, serta file `requirements.txt`, `render.yaml`, dan lainnya), lalu seret ke halaman GitHub.

      > Penting: yang diunggah adalah **isi** folder `software`, bukan folder `software`-nya. File `render.yaml` harus berada di halaman utama repository.

   4. Tunggu sampai semua file selesai terunggah, lalu klik **Commit changes**.

## Bagian B — Jalankan di Render

1. Buka **https://render.com**, klik **Get Started**, lalu pilih **GitHub** supaya bisa login memakai akun GitHub tadi.
2. Di dashboard Render, klik **New +** (kanan atas), lalu pilih **Blueprint**.
3. Klik **Connect** di samping repository `ina-agro-garlic`. Kalau repository-nya belum muncul, klik **Configure account** dan beri Render akses ke repository itu.
4. Render akan membaca file `render.yaml` secara otomatis. Isi **Blueprint Name** dengan `ina-agro-garlic`, lalu klik **Apply**.
5. Tunggu 3–6 menit selama Render memasang aplikasinya. Status yang muncul berurutan *Building*, lalu *Deploying*, lalu **Live**.
6. Klik nama layanan **ina-agro-garlic**. Link publiknya ada di bagian atas, misalnya `https://ina-agro-garlic.onrender.com`. Buka link itu, dan aplikasinya sudah bisa dipakai siapa saja.

## Hal yang perlu diketahui (paket gratis)

- **Tidur saat tidak dipakai.** Kalau 15 menit tidak ada yang membuka, server akan "tidur". Pengunjung berikutnya perlu menunggu sekitar 30–60 detik sampai halaman muncul. Ini normal. Sebelum demo atau presentasi, buka link-nya sekali beberapa menit lebih awal.
- **Akun dan riwayat bisa hilang.** Data akun dan riwayat disimpan di file SQLite. Di paket gratis, file ini akan **terhapus setiap kali server diperbarui atau dinyalakan ulang**. Untuk prototipe tugas ini tidak masalah. Kalau nanti butuh data yang permanen, database bisa dipindah ke Supabase atau Render PostgreSQL.
- **Update otomatis.** Setiap kali kode di GitHub berubah, Render akan otomatis memperbarui webnya.

## Kalau ada masalah

- **Status "Failed" di Render:** buka tab **Logs**, salin baris merah terakhir, lalu kirim ke Claude.
- **Halaman tidak muncul setelah lama menunggu:** muat ulang (refresh) halamannya. Server mungkin baru bangun dari tidur.

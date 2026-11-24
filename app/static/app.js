/* INA Agro-GARLIC — frontend (vanilla JS + Leaflet). Layar: Login, Home, Analisis, Hasil, Peta, Profil. */
const S = {
  token: localGet("ag_token"),
  user: null,
  tamu: localGet("ag_tamu") === "1",
  consentTamu: localGet("ag_consent") === "1",
  lokasi: { lat: -7.334, lon: 110.036 },  // default: Kledung, Temanggung
  data: null,          // data otomatis lokasi
  manual: {},          // nilai manual dari uji tanah
  modeManual: false,
  hasil: null,
  kriteria: null,
  info: null,          // mode & sumber data
  maps: [],
};
const WARNA = { S1: "#1f7a3a", S2: "#7a9a1f", S3: "#c27c0e", N: "#b3261e" };
const $ = (s) => document.querySelector(s);

function localGet(k) { try { return localStorage.getItem(k); } catch { return null; } }
function localSet(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function angka(v) { return typeof v === "number" ? String(v).replace(".", ",") : esc(v); }

async function api(path, opt = {}) {
  const headers = { "Content-Type": "application/json" };
  if (S.token) headers.Authorization = "Bearer " + S.token;
  const r = await fetch(path, { ...opt, headers, body: opt.body ? JSON.stringify(opt.body) : undefined });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail?.error || j.detail?.[0]?.msg || "Terjadi kesalahan (" + r.status + ")");
  return j;
}

function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 3200);
}
function modal(html) { $("#modal-body").innerHTML = html; $("#modal").hidden = false; }
function tutupModal() { $("#modal").hidden = true; }

function adaConsent() { return S.user ? S.user.consent : S.consentTamu; }
function masukAtauTamu() { return !!S.user || S.tamu; }

/* ---------------- router ---------------- */
const LAYAR = { login: layarLogin, home: layarHome, analisis: layarAnalisis, hasil: layarHasil, peta: layarPeta, profil: layarProfil };

async function route() {
  S.maps.forEach((m) => m.remove()); S.maps = [];
  let r = location.hash.slice(1) || "home";
  if (!masukAtauTamu()) r = "login";
  if (r === "hasil" && !S.hasil) r = "analisis";
  const fn = LAYAR[r] || layarHome;
  $("#header").hidden = $("#footer").hidden = r === "login";
  document.body.classList.toggle("is-login", r === "login");
  const tab = r === "hasil" ? "analisis" : r;
  document.querySelectorAll(".site-nav a").forEach((a) => a.classList.toggle("on", a.dataset.tab === tab));
  $("#user-label").textContent = S.user ? (S.user.nama || S.user.kontak) : "Mode tamu";
  window.scrollTo(0, 0);
  await fn();
}
window.addEventListener("hashchange", route);
function go(h) { if (location.hash === h) route(); else location.hash = h; }

async function init() {
  if (S.token) {
    try { S.user = await api("/api/v1/akun"); } catch { S.token = null; localSet("ag_token", null); }
  }
  try { S.kriteria = await api("/api/v1/kriteria"); } catch {}
  try { S.info = await api("/api/v1/info-data"); } catch {}
  route();
}

/* ---------------- Layar 1: Login ---------------- */
const LOGO = `<svg class="logo" viewBox="0 0 120 120" aria-hidden="true">
  <circle cx="60" cy="60" r="58" fill="#e7efe2"/>
  <path d="M60 22c3 10 8 13 8 13s20 8 20 33c0 18-13 28-28 28S32 86 32 68c0-25 20-33 20-33s5-3 8-13z" fill="#fff" stroke="#2f6b3a" stroke-width="3"/>
  <path d="M60 36c-6 12-8 30 0 59M60 36c6 12 8 30 0 59M47 45c-8 12-7 32 6 48M73 45c8 12 7 32-6 48" fill="none" stroke="#2f6b3a" stroke-width="2"/>
  <path d="M60 22c-2-6 0-10 4-14" fill="none" stroke="#2f6b3a" stroke-width="3" stroke-linecap="round"/></svg>`;

function layarLogin(daftar = false) {
  $("#view").innerHTML = `
  <section class="login-split">
    <div class="login-intro">
      ${LOGO}
      <h1>INA Agro-GARLIC</h1>
      <p class="lead">Cek kesesuaian lahan bawang putih berbasis data agroekologi.</p>
      <ul class="fitur">
        <li><b>Pilih lokasi lahan</b> di peta, lewat pencarian desa, atau koordinat.</li>
        <li><b>Data otomatis</b> suhu, curah hujan, tanah, dan lereng (BMKG, BBSDLP, DEM).</li>
        <li><b>Kelas S1/S2/S3/N</b> beserta faktor pembatas dan rekomendasi budidaya.</li>
        <li><b>Laporan PDF</b> dan riwayat analisis tersimpan.</li>
      </ul>
      <p class="small">Metode sistem pakar rule-based (FAO 1976 / juknis BBSDLP).</p>
    </div>
    <div class="login-card">
      <h2>${daftar ? "Daftar akun baru" : "Masuk"}</h2>
      <form id="f-login" autocomplete="on">
        ${daftar ? `<label class="field"><span>Nama lengkap</span><input id="nama" autocomplete="name"></label>` : ""}
        <label class="field"><span>No. HP / Email</span><input id="kontak" autocomplete="username" required></label>
        <label class="field"><span>Kata sandi${daftar ? " (min. 6 karakter)" : ""}</span><input id="sandi" type="password" autocomplete="${daftar ? "new-password" : "current-password"}" required></label>
        <div id="err" class="error" hidden></div>
        <button class="btn primary" type="submit">${daftar ? "Daftar" : "Masuk"}</button>
        <button class="btn" type="button" id="b-toggle">${daftar ? "Sudah punya akun? Masuk" : "Daftar akun baru"}</button>
      </form>
      ${daftar ? "" : `<p class="center"><button class="link muted" id="b-lupa">Lupa kata sandi?</button></p>`}
      <label class="consent"><input type="checkbox" id="consent" ${S.consentTamu ? "checked" : ""}>
        <span>Saya setuju lokasi lahan saya dipakai <b>hanya</b> untuk analisis kesesuaian lahan (opt-in, bisa dicabut di Pengaturan Akun). <button type="button" class="link" id="b-privasi">Baca kebijakan privasi</button></span></label>
      <div class="sep"><span>atau</span></div>
      <button class="btn" id="b-tamu">Coba tanpa akun (mode tamu)</button>
    </div>
  </section>`;
  $("#b-toggle").onclick = () => layarLogin(!daftar);
  $("#b-privasi").onclick = kebijakanPrivasi;
  if ($("#b-lupa")) $("#b-lupa").onclick = () => modal(`<h3>Lupa kata sandi</h3><p>Pada prototipe ini reset kata sandi belum tersedia. Silakan daftar akun baru atau hubungi admin/penyuluh pendamping.</p>`);
  $("#b-tamu").onclick = () => {
    const c = $("#consent").checked;
    S.tamu = true; S.consentTamu = c; localSet("ag_tamu", "1"); localSet("ag_consent", c ? "1" : "0");
    go("#analisis");
  };
  $("#f-login").onsubmit = async (e) => {
    e.preventDefault();
    const err = $("#err"); err.hidden = true;
    const consent = $("#consent").checked;
    try {
      const body = { kontak: $("#kontak").value, sandi: $("#sandi").value };
      const r = daftar ? await api("/api/v1/auth/daftar", { method: "POST", body: { ...body, nama: $("#nama").value, consent } })
                       : await api("/api/v1/auth/masuk", { method: "POST", body });
      S.token = r.token; S.user = r.user; localSet("ag_token", r.token);
      if (consent && !S.user.consent) { await api("/api/v1/akun/consent", { method: "PUT", body: { consent: true } }); S.user.consent = true; }
      S.tamu = false; localSet("ag_tamu", null);
      go("#home");
    } catch (ex) { err.textContent = ex.message; err.hidden = false; }
  };
}

function kebijakanPrivasi() {
  modal(`<h3>Kebijakan privasi (ringkas)</h3>
  <ul class="rek"><li>Koordinat lahan hanya dipakai untuk mengambil data agroekologi dan menghitung kelas kesesuaian.</li>
  <li>Lokasi tidak dibagikan ke pihak lain dan tidak dipakai untuk iklan.</li>
  <li>Persetujuan (opt-in) dapat dicabut kapan saja di menu Profil &gt; Pengaturan Akun; setelah dicabut, analisis tidak dapat dijalankan.</li>
  <li>Riwayat analisis hanya disimpan bila Anda menekan tombol Simpan, dan dapat dihapus.</li></ul>`);
}

/* ---------------- Home ---------------- */
async function layarHome() {
  const nama = S.user ? (S.user.nama || S.user.kontak) : "Tamu";
  $("#view").innerHTML = `
  <div class="hero">
    <div><h1>Selamat datang, ${esc(nama)}</h1>
      <p>Pilih titik lahan di peta, sistem mengambil data iklim, tanah, dan lereng, lalu menentukan kelas kesesuaian lahan untuk bawang putih beserta faktor pembatas dan rekomendasinya.</p></div>
    <div class="hero-act"><a class="btn big" href="#analisis">Mulai analisis lahan</a><a class="btn ghost" href="#peta">Lihat peta kesesuaian</a></div>
  </div>
  <div class="grid-3">
    <div class="card"><h3>Arti kelas kesesuaian</h3>
      <div class="kelas-list">
        <div><span class="badge bg-S1">S1</span> Sangat sesuai</div><div><span class="badge bg-S2">S2</span> Cukup sesuai</div>
        <div><span class="badge bg-S3">S3</span> Sesuai marginal</div><div><span class="badge bg-N">N</span> Tidak sesuai</div></div>
      <p class="small muted">Kelas akhir mengikuti parameter terburuk (hukum minimum). Parameter itulah yang disebut faktor pembatas.</p></div>
    <div class="card" id="home-riw"><h3>Analisis tersimpan terakhir</h3><div class="muted small">${S.user ? "Memuat…" : "Masuk dengan akun untuk menyimpan riwayat analisis."}</div></div>
    <div class="card"><h3>${S.info?.mode === "riil" ? `Sentra bawang putih (${S.info.jumlah_unit} unit lahan riil)` : "Kawasan cakupan (MVP)"}</h3><div id="home-kaw" class="small muted">Memuat…</div></div>
  </div>`;
  api("/api/v1/kawasan").then((k) => {
    $("#home-kaw").innerHTML = k.map((x) => `• ${esc(x.nama)}, Kab. ${esc(x.kabupaten)} — <button class="link" data-c="${x.pusat}">analisis di sini</button>`).join("<br>");
    document.querySelectorAll("#home-kaw [data-c]").forEach((b) => (b.onclick = () => {
      const [lat, lon] = b.dataset.c.split(",").map(Number); setLokasi(lat, lon, false); location.hash = "#analisis";
    }));
  }).catch(() => {});
  if (S.user) {
    try {
      const r = await api("/api/v1/riwayat");
      $("#home-riw").innerHTML = `<h3>Analisis tersimpan terakhir</h3>` + (r.length ? r.slice(0, 3).map(itemRiwayat).join("") : `<div class="muted small">Belum ada. Hasil analisis yang Anda simpan akan muncul di sini.</div>`);
      pasangRiwayat();
    } catch {}
  }
}

function itemRiwayat(h) {
  return `<div class="riw" data-id="${esc(h.analysis_id)}"><span class="badge bg-${h.kelas_akhir}">${h.kelas_akhir}</span>
    <div class="grow"><b>Desa ${esc(h.lokasi.desa)}</b>, ${esc(h.lokasi.kabupaten)}<div class="small muted">${esc((h.disimpan_pada || h.waktu || "").replace("T", " "))} · ${esc(h.label)}</div></div><span class="muted">›</span></div>`;
}
function pasangRiwayat() {
  document.querySelectorAll(".riw[data-id]").forEach((el) => (el.onclick = async () => {
    S.hasil = await api("/api/v1/analisis/" + el.dataset.id); S.hasil._tersimpan = true; location.hash = "#hasil";
  }));
}

function bantuan() {
  modal(`<h3>Cara pakai</h3><ol class="rek">
  <li>Cari nama desa/kecamatan atau ketik koordinat (mis. <i>-7.33, 110.04</i>), atau klik peta / tombol <b>Lokasi saya</b>.</li>
  <li>Periksa <b>data otomatis</b> lokasi. Jika punya hasil uji tanah sendiri, klik <b>Ubah manual</b>.</li>
  <li>Klik <b>Analisis Kesesuaian</b> untuk melihat kelas, faktor pembatas, dan rekomendasi.</li></ol>
  ${S.info?.mode === "riil" ? `<p class="small muted">Data riil: tanah dari SoilGrids (ISRIC, 250 m), iklim dari ERA5 2014–2023, lereng dari Copernicus DEM 90 m. Titik di dalam ${S.info.jumlah_kawasan} sentra tampil instan; titik lain di Indonesia diambil langsung (±5–10 detik). Drainase masih estimasi dari tekstur dan lereng. Ambang kriteria belum dikalibrasi pakar.</p>` : `<p class="small muted">Prototipe: data lokasi masih data contoh untuk 3 kawasan (Temanggung, Sembalun, Tawangmangu) dan ambang kriteria belum dikalibrasi pakar.</p>`}`);
}

/* ---------------- Layar 2: Analisis Lahan ---------------- */
async function layarAnalisis() {
  $("#view").innerHTML = `
  <div class="page-head"><div><h1>Analisis Lahan</h1><p class="muted">Pilih lokasi lahan, periksa datanya, lalu jalankan analisis kesesuaian.</p></div></div>
  <div class="layout-2">
    <section class="col-map">
      <div class="search"><span class="mag">⌕</span><input id="q" placeholder="Cari desa / kecamatan / koordinat (mis. -7.33, 110.04)" autocomplete="off"><div id="sug" class="suggest" hidden></div></div>
      <div class="map-wrap"><div id="map" class="map tall"></div><button class="locbtn" id="b-gps">◎ Lokasi saya</button></div>
      <div class="coord" id="coord"></div>
    </section>
    <aside class="col-side">
      <div class="card" id="data-card"><h3>Data otomatis lokasi ini</h3><div id="data-isi" class="muted small">Memuat…</div></div>
      ${adaConsent() ? "" : `<div class="note">Anda belum menyetujui penggunaan lokasi untuk analisis. <button class="link" id="b-izin">Setujui sekarang</button></div>`}
      <button class="btn primary big" id="b-analisis">Analisis Kesesuaian</button>
      <div id="err" class="error" hidden></div>
    </aside>
  </div>`;

  const map = L.map("map", { zoomControl: true }).setView([S.lokasi.lat, S.lokasi.lon], 13);
  S.maps.push(map);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap" }).addTo(map);
  api("/api/v1/kawasan").then((ks) => ks.forEach((k) => L.rectangle([[k.bbox.lat_min, k.bbox.lon_min], [k.bbox.lat_max, k.bbox.lon_max]],
    { color: "#2f6b3a", weight: 1.5, fill: false, dashArray: "5 5", interactive: false }).addTo(map))).catch(() => {});
  const pin = L.marker([S.lokasi.lat, S.lokasi.lon], { draggable: true }).addTo(map);
  pin.on("dragend", () => { const p = pin.getLatLng(); setLokasi(p.lat, p.lng); });
  map.on("click", (e) => { pin.setLatLng(e.latlng); setLokasi(e.latlng.lat, e.latlng.lng); });
  S._pin = pin; S._map = map;
  setTimeout(() => { map.invalidateSize(); map.setView([S.lokasi.lat, S.lokasi.lon]); }, 50);

  $("#b-gps").onclick = () => {
    if (!navigator.geolocation) return toast("Perangkat tidak mendukung GPS");
    navigator.geolocation.getCurrentPosition((p) => setLokasi(p.coords.latitude, p.coords.longitude, true),
      () => toast("Lokasi tidak dapat diakses. Izinkan akses lokasi di browser."), { enableHighAccuracy: true, timeout: 10000 });
  };
  if ($("#b-izin")) $("#b-izin").onclick = berikanConsent;
  pasangPencarian();
  $("#b-analisis").onclick = jalankanAnalisis;
  setLokasi(S.lokasi.lat, S.lokasi.lon, false);
}

async function berikanConsent() {
  if (S.user) { await api("/api/v1/akun/consent", { method: "PUT", body: { consent: true } }); S.user.consent = true; }
  else { S.consentTamu = true; localSet("ag_consent", "1"); }
  toast("Persetujuan disimpan"); route();
}

function pasangPencarian() {
  const q = $("#q"), sug = $("#sug");
  let t;
  q.oninput = () => {
    clearTimeout(t);
    const v = q.value.trim();
    const m = v.match(/^(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)$/);
    if (m) {
      sug.innerHTML = `<button data-lat="${m[1]}" data-lon="${m[2]}">Ke koordinat ${esc(m[1])}, ${esc(m[2])}</button>`; sug.hidden = false; pasang(); return;
    }
    if (v.length < 2) { sug.hidden = true; return; }
    t = setTimeout(async () => {
      const r = await api("/api/v1/cari?q=" + encodeURIComponent(v)).catch(() => []);
      sug.innerHTML = r.length ? r.map((x) => `<button data-lat="${x.lat}" data-lon="${x.lon}"><b>${esc(x.nama)}</b> <span class="small muted">${esc(x.keterangan)}</span></button>`).join("")
                               : `<button disabled>Tidak ditemukan</button>`;
      sug.hidden = false; pasang();
    }, 200);
  };
  q.onkeydown = (e) => { if (e.key === "Enter") { const b = sug.querySelector("button[data-lat]"); if (b) b.click(); } };
  function pasang() {
    sug.querySelectorAll("button[data-lat]").forEach((b) => (b.onclick = () => {
      setLokasi(parseFloat(b.dataset.lat), parseFloat(b.dataset.lon), true); sug.hidden = true; q.value = b.textContent.trim();
    }));
  }
  document.addEventListener("click", (e) => { if (!e.target.closest(".search")) sug.hidden = true; }, { once: true });
}

async function setLokasi(lat, lon, geser = false) {
  S.lokasi = { lat, lon };
  if (S._pin && $("#map")) {
    S._pin.setLatLng([lat, lon]);
    if (geser) S._map.setView([lat, lon], Math.max(S._map.getZoom(), 14));
  }
  if (!$("#coord")) return;
  $("#coord").textContent = `Koordinat: ${lat.toFixed(5)}, ${lon.toFixed(5)} · klik peta atau geser pin untuk memindah`;
  const sedang = setTimeout(() => { if ($("#data-isi")) $("#data-isi").innerHTML = `<div class="muted small">Mengambil data riil tanah, iklim, dan lereng untuk titik ini… (±5–10 detik)</div>`; }, 400);
  const req = (S._req = (S._req || 0) + 1);
  try {
    const d = await api(`/api/v1/data-lokasi?lat=${lat}&lon=${lon}`);
    clearTimeout(sedang);
    if (req !== S._req) return;  // pengguna sudah memilih titik lain
    S.data = d;
  } catch (ex) {
    clearTimeout(sedang);
    if (req !== S._req) return;
    S.data = null;
    $("#data-isi").innerHTML = `<div class="error">${esc(ex.message)}.</div><div class="small muted">${S.info?.mode === "riil" ? "Pilih titik daratan di Indonesia. Sentra yang datanya sudah dikumpulkan ditandai kotak garis putus-putus." : "Kawasan cakupan ditandai kotak garis putus-putus di peta. Coba cari \"Kledung\", \"Sembalun\", atau \"Tawangmangu\"."}</div>`;
    return;
  }
  renderData();
}

function renderData() {
  const d = S.data, K = S.kriteria?.parameter || {};
  const baris = Object.keys(K).map((k) => {
    const p = K[k];
    const auto = d.nilai[k];
    const manual = S.manual[k];
    let isi;
    if (S.modeManual) {
      isi = p.jenis === "numerik"
        ? `<input type="text" inputmode="decimal" data-k="${k}" value="${manual ?? ""}" placeholder="${auto ?? "—"}">`
        : `<select data-k="${k}"><option value="">${auto ? "otomatis: " + esc(auto) : "—"}</option>${Object.keys(p.pilihan).map((o) => `<option ${manual === o ? "selected" : ""}>${o}</option>`).join("")}</select>`;
    } else {
      const v = manual ?? auto;
      isi = v == null ? `<span class="na">tidak tersedia</span>` : `${angka(v)} ${esc(p.satuan)}`;
    }
    const sb = d.sumber?.[k] || p.sumber;
    const src = manual != null && manual !== "" ? `<span class="manual">manual</span>` : (sb === "estimasi" ? `<span class="est">estimasi</span>` : esc(sb));
    return `<tr><td>${esc(p.label)}</td><td class="${S.modeManual ? "edit" : ""}">${isi}</td><td class="src">${src}</td></tr>`;
  }).join("");
  const nManual = Object.values(S.manual).filter((v) => v !== "" && v != null).length;
  const lengkap = Object.keys(K).filter((k) => (S.manual[k] ?? d.nilai[k]) != null && (S.manual[k] ?? d.nilai[k]) !== "").length;
  $("#data-isi").classList.remove("muted", "small");
  $("#data-isi").innerHTML = `
    <div class="small muted" style="margin-bottom:6px">Desa ${esc(d.lokasi.desa)}, ${d.lokasi.kecamatan && d.lokasi.kecamatan !== "-" ? `Kec. ${esc(d.lokasi.kecamatan)}, ` : ""}Kab. ${esc(d.lokasi.kabupaten)} · elevasi ±${d.elevasi_m} mdpl</div>
    <table><tbody>${baris}</tbody></table>
    <div class="small muted" style="margin-top:8px">Kelengkapan data: ${lengkap}/${Object.keys(K).length}${nManual ? ` · ${nManual} nilai manual` : ""} ·
      <button class="link" id="b-manual">${S.modeManual ? "Selesai ubah" : "Ubah manual"}</button>
      ${nManual ? ` · <button class="link" id="b-reset">Pakai data otomatis</button>` : ""}</div>`;
  $("#b-manual").onclick = () => { bacaManual(); S.modeManual = !S.modeManual; renderData(); };
  if ($("#b-reset")) $("#b-reset").onclick = () => { S.manual = {}; S.modeManual = false; renderData(); };
}

function bacaManual() {
  document.querySelectorAll("#data-isi [data-k]").forEach((el) => {
    const v = el.value.trim();
    if (v === "") delete S.manual[el.dataset.k];
    else S.manual[el.dataset.k] = el.tagName === "INPUT" ? parseFloat(v.replace(",", ".")) : v;
  });
}

async function jalankanAnalisis() {
  if (S.modeManual) { bacaManual(); S.modeManual = false; renderData(); }
  const err = $("#err"); err.hidden = true;
  if (!adaConsent()) { err.textContent = "Setujui penggunaan lokasi untuk analisis terlebih dahulu."; err.hidden = false; return; }
  const b = $("#b-analisis"); b.disabled = true; b.textContent = "Menganalisis…";
  try {
    S.hasil = await api("/api/v1/analisis", { method: "POST", body: {
      lat: S.lokasi.lat, lon: S.lokasi.lon, user_id: S.user?.id || null, consent: adaConsent(), parameter_manual: S.manual } });
    location.hash = "#hasil";
  } catch (ex) { err.textContent = ex.message; err.hidden = false; }
  finally { b.disabled = false; b.textContent = "Analisis Kesesuaian"; }
}

/* ---------------- Layar 3: Hasil Kesesuaian ---------------- */
function layarHasil() {
  const h = S.hasil, K = S.kriteria?.parameter || {};
  const pembatas = h.faktor_pembatas_kode;
  const lain = Object.keys(h.kelas_per_parameter).filter((k) => !pembatas.includes(k));
  const ringkasLain = lain.length ? `${lain.length} parameter lain: ` + ringkasKelas(lain.map((k) => h.kelas_per_parameter[k].kelas)) : "";
  const baris = (k) => {
    const d = h.kelas_per_parameter[k];
    return `<tr><td>${esc(K[k]?.label || k)}${d.sumber === "manual" ? ` <span class="manual">manual</span>` : ""}</td>
      <td>${angka(d.nilai)}${esc(d.satuan === "%" ? "%" : "")}${d.dekat_ambang ? " *" : ""}</td><td>ideal ${esc(d.ideal)}</td><td class="k kelas-${d.kelas}">${d.kelas}</td></tr>`;
  };
  $("#view").innerHTML = `
  <div class="page-head"><div><a class="back" href="#analisis">← Kembali ke Analisis Lahan</a><h1>Hasil Kesesuaian</h1>
    <p class="muted">Desa ${esc(h.lokasi.desa)}, ${h.lokasi.kecamatan && h.lokasi.kecamatan !== "-" ? `Kec. ${esc(h.lokasi.kecamatan)}, ` : ""}Kab. ${esc(h.lokasi.kabupaten)} · ${h.lokasi.lat.toFixed(5)}, ${h.lokasi.lon.toFixed(5)}</p></div>
    <div class="head-act"><button class="btn" id="b-simpan">${h._tersimpan ? "Tersimpan ✓" : "Simpan ke riwayat"}</button>
      <a class="btn primary" href="/api/v1/analisis/${encodeURIComponent(h.analysis_id)}/pdf">Unduh PDF</a>
      <button class="btn-sm" id="b-menu" aria-label="Menu lain">⋯</button></div></div>
  <div class="layout-2 hasil">
    <section>
      <div class="card hasil-head">
        <div class="kelas-box kelas-${h.kelas_akhir}">${h.kelas_akhir}</div>
        <div><div class="label">${esc(h.label)}</div>
          <div>${esc(h.penjelasan)}</div>
          <div class="muted small">Kelengkapan data ${esc(h.kelengkapan_data)} · elevasi ±${h.elevasi_m ?? "-"} mdpl</div></div>
      </div>
      <div class="card"><h3>${pembatas.length ? `Kenapa ${h.kelas_akhir}? Faktor pembatas` : "Tidak ada faktor pembatas"}</h3>
        <table><thead><tr><th>Parameter</th><th>Nilai</th><th>Ideal (S1)</th><th>Kelas</th></tr></thead><tbody>${pembatas.map(baris).join("")}
          <tr id="tr-lain"><td colspan="4" class="muted">${pembatas.length ? ringkasLain : "Semua parameter: S1"} · <button class="link" id="b-semua">lihat semua</button></td></tr>
          ${lain.map((k) => baris(k).replace("<tr>", '<tr class="lain" hidden>')).join("")}
        </tbody></table>
        ${h.parameter_dekat_ambang.length ? `<p class="small muted">* nilai dekat ambang batas kelas: ${esc(h.parameter_dekat_ambang.join(", "))}</p>` : ""}
        ${h.parameter_hilang.length ? `<p class="small" style="color:var(--N)">Data tidak tersedia: ${esc(h.parameter_hilang.join(", "))}</p>` : ""}
      </div>
      ${kartuPanen(h)}
      <div class="card"><h3>Rekomendasi</h3><ul class="rek">${h.rekomendasi.map((r) => `<li>${esc(r)}</li>`).join("")}</ul></div>
    </section>
    <aside class="col-side">
      <div class="card"><h3>Lokasi lahan</h3><div id="minimap" class="map mini"></div></div>
      <div class="note">${h.perlu_verifikasi_lapangan ? "<b>Disarankan verifikasi lapangan oleh penyuluh</b> karena data tidak lengkap atau ada nilai dekat ambang batas." : "Disarankan verifikasi lapangan oleh penyuluh sebelum tanam."}</div>
      <p class="small muted">ID ${esc(h.analysis_id)} · diproses ${angka(h.waktu_proses_ms)} ms</p>
    </aside>
  </div>`;

  $("#b-semua").onclick = () => {
    const rows = document.querySelectorAll("tr.lain"); const buka = rows[0]?.hidden;
    rows.forEach((r) => (r.hidden = !buka)); $("#b-semua").textContent = buka ? "sembunyikan" : "lihat semua";
  };
  $("#b-menu").onclick = () => modal(`<h3>Menu</h3><p><a href="#analisis" onclick="tutupModal()">Analisis lokasi lain</a></p>
    <p><button class="link" onclick="tutupModal();window.print()">Cetak halaman</button></p>
    <p><button class="link" onclick="salinJSON()">Salin hasil (JSON)</button></p>`);
  $("#b-simpan").onclick = async () => {
    if (!S.user) { modal(`<h3>Simpan memerlukan akun</h3><p>Mode tamu tidak menyimpan riwayat. Masuk atau daftar untuk menyimpan, atau tekan <b>Unduh PDF</b> untuk menyimpan laporan ke perangkat.</p><p><a href="#login" onclick="tutupModal();keluarTamu()">Masuk / daftar</a></p>`); return; }
    try { await api("/api/v1/riwayat/" + h.analysis_id, { method: "POST" }); h._tersimpan = true; $("#b-simpan").textContent = "Tersimpan ✓"; toast("Disimpan ke riwayat"); }
    catch (ex) { toast(ex.message); }
  };
  const m = L.map("minimap", { scrollWheelZoom: false })
    .setView([h.lokasi.lat, h.lokasi.lon], 14);
  S.maps.push(m);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap" }).addTo(m);
  L.circleMarker([h.lokasi.lat, h.lokasi.lon], { radius: 10, color: WARNA[h.kelas_akhir], fillOpacity: .8 }).addTo(m);
}

function kartuPanen(h) {
  const p = h.prediksi_panen;
  if (!p) return `<div class="card"><h3>Prediksi hasil panen (ML)</h3><p class="small muted">Model belum tersedia untuk lokasi ini (model belum dilatih atau ada parameter yang kosong).</p></div>`;
  const [lo, hi] = p.rentang_ton_per_ha, maks = Math.max(hi, p.rerata_sentra_ton_per_ha || 0) * 1.25 || 1;
  const pct = (v) => Math.min(100, (100 * v) / maks).toFixed(1) + "%";
  return `<div class="card panen"><h3>Prediksi hasil panen <span class="tag-ai">ML · ${esc(p.model)}</span></h3>
    <div class="panen-angka"><b>${angka(p.ton_per_ha)}</b> ton/ha <span class="muted small">rentang ${angka(lo)}–${angka(hi)} ton/ha</span></div>
    <div class="bar"><span class="rng" style="left:${pct(lo)};width:calc(${pct(hi)} - ${pct(lo)})"></span><span class="pt" style="left:${pct(p.ton_per_ha)}"></span>
      ${p.rerata_sentra_ton_per_ha ? `<span class="avg" style="left:${pct(p.rerata_sentra_ton_per_ha)}" title="rata-rata sentra"></span>` : ""}</div>
    <p class="small muted">Rata-rata produktivitas sentra (BPS): ${angka(p.rerata_sentra_ton_per_ha)} ton/ha · galat rata-rata saat diuji ±${angka(p.mae_ton_per_ha)} ton/ha. ${esc(p.catatan)} <button class="link" onclick="infoModel()">tentang model</button></p>
    ${p.dalam_data_latih ? "" : `<div class="note small">Lokasi ini di luar kabupaten yang ada di data latih. Saat diuji pada kabupaten baru, model belum lebih akurat daripada rata-rata sentra, jadi anggap angka ini perkiraan kasar.</div>`}</div>`;
}
async function infoModel() {
  const m = await api("/api/v1/model-panen").catch(() => null);
  if (!m || m.tersedia === false) return modal("<h3>Model prediksi panen</h3><p>Model belum dilatih.</p>");
  modal(`<h3>Model prediksi hasil panen</h3>
    <p>${esc(m.model)} dilatih dengan ${m.jumlah_data} data produktivitas riil (${esc(m.sumber_target)}) dari ${m.jumlah_kabupaten} kabupaten, tahun ${m.tahun[0]}–${m.tahun[1]}. Fitur: cuaca tahun itu (ERA5) dan karakteristik lahan sentra (SoilGrids, DEM).</p>
    <p><b>Evaluasi (galat rata-rata/MAE, makin kecil makin baik):</b></p>
    <table><thead><tr><th>Skenario uji</th><th>Model</th><th>Tanpa model (rata-rata)</th></tr></thead><tbody>
      <tr><td>Tahun baru di kabupaten yang sudah dikenal</td><td><b>${angka(m.evaluasi_tahun_baru.mae_ton_ha)}</b> ton/ha</td><td>${angka(m.evaluasi_tahun_baru.mae_baseline_ton_ha)} ton/ha</td></tr>
      <tr><td>Kabupaten baru (belum pernah dilihat)</td><td><b>${angka(m.evaluasi_kabupaten_baru.mae_ton_ha)}</b> ton/ha</td><td>${angka(m.evaluasi_kabupaten_baru.mae_baseline_ton_ha)} ton/ha</td></tr></tbody></table>
    <p class="small muted">Model membantu menebak hasil di sentra yang datanya sudah ada, tetapi belum bisa diandalkan untuk lokasi baru karena data latih baru mencakup ${m.jumlah_kabupaten} kabupaten. Akurasinya akan naik bila data kabupaten lain ditambahkan.</p>
    <p><b>Faktor paling berpengaruh:</b></p><table><tbody>${Object.entries(m.kepentingan_fitur).map(([k, v]) => `<tr><td>${esc(k)}</td><td><div class="imp" style="width:${(v * 100).toFixed(0)}%"></div></td><td>${(v * 100).toFixed(0)}%</td></tr>`).join("")}</tbody></table>`);
}

function ringkasKelas(arr) {
  const c = {}; arr.forEach((k) => (c[k] = (c[k] || 0) + 1));
  return Object.entries(c).map(([k, n]) => (Object.keys(c).length === 1 ? k : `${n}×${k}`)).join(", ");
}
function salinJSON() { navigator.clipboard?.writeText(JSON.stringify(S.hasil, null, 2)); toast("Hasil disalin"); tutupModal(); }
function keluarTamu() { S.tamu = false; localSet("ag_tamu", null); }

/* ---------------- Peta kawasan ---------------- */
async function layarPeta() {
  $("#view").innerHTML = `
  <div class="page-head"><div><h1>Peta Kesesuaian</h1><p class="muted">Unit lahan (petak ±2 km) di sentra bawang putih, diwarnai menurut kelas kesesuaiannya. Klik petak untuk detail.</p></div></div>
  <div class="layout-2 peta">
    <section><div id="pmap" class="map full"></div></section>
    <aside class="col-side">
      <div class="card"><h3>Kawasan</h3><div class="chips" id="chips"></div></div>
      <div class="card"><h3>Legenda</h3><div class="legend">${["S1", "S2", "S3", "N"].map((k) => `<span style="--c:${WARNA[k]}">${k} · ${esc(S.kriteria?.label_kelas?.[k] || "")}</span>`).join("")}</div></div>
      <div class="card"><h3>Ringkasan kawasan</h3><div id="ringkas" class="small"></div></div>
      <p class="small muted">${S.info?.mode === "riil" ? "Sumber: SoilGrids (ISRIC), ERA5 (Open-Meteo), Copernicus DEM. Drainase diestimasi." : "Data petak masih data contoh sampai data riil dimuat."}</p>
    </aside>
  </div>`;
  const map = L.map("pmap"); S.maps.push(map);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap" }).addTo(map);
  const [kaw, units] = await Promise.all([api("/api/v1/kawasan"), api("/api/v1/peta-kesesuaian")]);
  units.forEach((u) => {
    const [a, b, c, d] = u.bbox;
    L.rectangle([[a, b], [c, d]], { color: WARNA[u.kelas], weight: .6, fillOpacity: .45 }).addTo(map)
      .bindPopup(`<b>Kelas ${u.kelas}</b><br>${u.faktor_pembatas.length ? "Pembatas: " + esc(u.faktor_pembatas.join(", ")) : "Tanpa faktor pembatas"}<br>Data ${u.kelengkapan_data}<br>
        <button class="link" onclick="analisisDi(${(a + c) / 2},${(b + d) / 2})">Analisis di sini ›</button>`);
  });
  const pilih = (k) => {
    map.fitBounds([[k.bbox.lat_min, k.bbox.lon_min], [k.bbox.lat_max, k.bbox.lon_max]]);
    document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("on", c.dataset.id === k.id));
    const uk = units.filter((u) => u.id.startsWith(k.id + "-")), n = {};
    uk.forEach((u) => (n[u.kelas] = (n[u.kelas] || 0) + 1));
    const fp = {}; uk.forEach((u) => u.faktor_pembatas.forEach((f) => (fp[f] = (fp[f] || 0) + 1)));
    const top = Object.entries(fp).sort((a, b) => b[1] - a[1]).slice(0, 3);
    $("#ringkas").innerHTML = `<b>${esc(k.nama)}</b>, Kab. ${esc(k.kabupaten)}<table style="margin:8px 0"><tbody>${["S1", "S2", "S3", "N"].map((c) =>
      `<tr><td><span class="badge bg-${c}">${c}</span></td><td>${n[c] || 0} petak</td><td>${Math.round(100 * (n[c] || 0) / uk.length)}%</td></tr>`).join("")}</tbody></table>
      <div class="muted">Faktor pembatas terbanyak: ${esc(top.map(([f, c]) => `${f} (${c})`).join(", ") || "-")}</div>`;
  };
  $("#chips").innerHTML = kaw.map((k) => `<button class="chip" data-id="${k.id}">${esc(k.kabupaten)}</button>`).join("");
  document.querySelectorAll(".chip").forEach((c) => (c.onclick = () => pilih(kaw.find((k) => k.id === c.dataset.id))));
  pilih(kaw[0]);
}
function analisisDi(lat, lon) { S.lokasi = { lat, lon }; S.manual = {}; location.hash = "#analisis"; }
function bantuanPeta() {
  modal(`<h3>Peta kesesuaian</h3><p>Tiap petak adalah satu unit lahan di kawasan cakupan MVP, diwarnai menurut kelas kesesuaiannya untuk bawang putih. Klik petak untuk melihat faktor pembatas, lalu "Analisis di sini" untuk rincian dan rekomendasi.</p><p class="small muted">Sumber data: SoilGrids (ISRIC), ERA5 (Open-Meteo), Copernicus DEM; drainase diestimasi dari tekstur dan lereng.</p>`);
}

/* ---------------- Profil ---------------- */
async function layarProfil() {
  const u = S.user;
  $("#view").innerHTML = `
  <div class="page-head"><div><h1>Akun &amp; Riwayat</h1><p class="muted">${u ? esc(u.nama || "Pengguna") + " · " + esc(u.kontak) : "Mode tamu: riwayat tidak disimpan. Masuk/daftar untuk menyimpan hasil analisis."}</p></div>
    <div class="head-act"><button class="btn" id="b-keluar">${u ? "Keluar" : "Masuk / daftar"}</button></div></div>
  <div class="layout-2">
    <section><div class="card" id="riw"><h3>Riwayat analisis</h3><div class="muted small">${u ? "Memuat…" : "Tersedia setelah masuk."}</div></div></section>
    <aside class="col-side">
      <div class="card"><h3>Pengaturan akun &amp; privasi</h3>
        <label class="switch"><span>Izinkan lokasi lahan dipakai untuk analisis kesesuaian (opt-in)</span><input type="checkbox" id="sw-consent" ${adaConsent() ? "checked" : ""}></label>
        <p class="small muted">Jika dicabut, analisis tidak dapat dijalankan. <button class="link" onclick="kebijakanPrivasi()">Kebijakan privasi</button></p></div>
      <div class="card"><h3>Tentang metode</h3><p class="small">Sistem pakar rule-based mengikuti kerangka FAO (1976) dan juknis BBSDLP (disederhanakan). Tujuh parameter dinilai: suhu, curah hujan, pH, C-organik, lereng, drainase, tekstur. Kelas akhir = kelas terburuk. Ambang kriteria disimpan di file JSON agar dapat dikalibrasi pakar.</p></div>
    </aside>
  </div>`;
  $("#sw-consent").onchange = async (e) => {
    const c = e.target.checked;
    if (u) { await api("/api/v1/akun/consent", { method: "PUT", body: { consent: c } }); u.consent = c; }
    else { S.consentTamu = c; localSet("ag_consent", c ? "1" : "0"); }
    toast(c ? "Persetujuan diberikan" : "Persetujuan dicabut");
  };
  $("#b-keluar").onclick = async () => {
    if (u) { await api("/api/v1/auth/keluar", { method: "POST" }).catch(() => {}); }
    S.user = null; S.token = null; S.tamu = false; S.hasil = null; localSet("ag_token", null); localSet("ag_tamu", null);
    go("#login");
  };
  if (u) {
    const r = await api("/api/v1/riwayat").catch(() => []);
    $("#riw").innerHTML = `<h3>Riwayat analisis</h3>` + (r.length ? r.map((h) => itemRiwayat(h).replace("<span class=\"muted\">›</span>",
      `<button class="link small" data-hapus="${esc(h.analysis_id)}">hapus</button>`)).join("") : `<div class="muted small">Belum ada analisis tersimpan.</div>`);
    pasangRiwayat();
    document.querySelectorAll("[data-hapus]").forEach((b) => (b.onclick = async (e) => {
      e.stopPropagation(); await api("/api/v1/riwayat/" + b.dataset.hapus, { method: "DELETE" }); toast("Dihapus dari riwayat"); layarProfil();
    }));
  }
}

init();

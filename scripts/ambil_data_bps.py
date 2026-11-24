"""
Mengambil data produksi & luas panen bawang putih per kabupaten dari WebAPI BPS.
Sumber tabel: BPS Provinsi Jawa Tengah (var 2116 luas panen, 2118 produksi sayuran semusim),
BPS Provinsi Jawa Barat (174/176), BPS Provinsi Sumatera Utara (534/541).

Jalankan (key TIDAK disimpan di kode):
    Linux/Mac : BPS_API_KEY=xxxx python scripts/ambil_data_bps.py
    Windows   : set BPS_API_KEY=xxxx  lalu  python scripts/ambil_data_bps.py
"""
import json, os, sys, urllib.request, time
K = os.environ.get('BPS_API_KEY') or sys.exit('Set BPS_API_KEY dulu (key dari https://webapi.bps.go.id/developer/)')
def get(path):
    for i in range(3):
        try:
            return json.load(urllib.request.urlopen(f"https://webapi.bps.go.id/v1/api/{path}/key/{K}/", timeout=60))
        except Exception as e:
            time.sleep(2); err = e
    raise err
def tahun(dom, var):
    out, page = [], 1
    while True:
        d = get(f"list/model/th/domain/{dom}/var/{var}/page/{page}")
        if not d.get('data') or len(d['data']) < 2: break
        out += d['data'][1]
        if page >= d['data'][0]['pages']: break
        page += 1
    return out
def data(dom, var, th_id):
    return get(f"list/model/data/domain/{dom}/var/{var}/th/{th_id}")

import json
def seri(dom, var, kab, kom='bawang putih', skala=1.0):
    """{tahun: nilai} untuk kabupaten `kab` & komoditas `kom` (dicari di turvar atau vervar)."""
    out = {}
    for t in tahun(dom, var):
        try: d = data(dom, var, t['th_id'])
        except Exception as e: continue
        dc = d.get('datacontent') or {}
        vv = d.get('vervar', []); tv = d.get('turvar', []); tt = d.get('turtahun', [{'val': 0}])
        vk = [v for v in vv if kab.lower() in v['label'].lower() and 'kota' not in v['label'].lower()]
        tk = [x for x in tv if kom in x['label'].lower()]
        if not vk:  # kabupaten level kecamatan: ambil baris total
            vk = [v for v in vv if v['label'].strip().lower() in ('jumlah', 'total', kab.lower(), 'kabupaten ' + kab.lower())]
        if not vk or (tv and not tk):
            continue
        tvv = tk[0]['val'] if tk else 0
        key = f"{vk[0]['val']}{var}{tvv}{t['th_id']}{tt[0]['val']}"
        if key in dc and dc[key] not in (None, ''):
            out[int(t['th'])] = float(dc[key]) * skala
    return out
rows = []
def tambah(kid, kab, luas, prod):
    for th in sorted(set(luas) & set(prod)):
        if luas[th] > 0 and prod[th] > 0:
            rows.append({'kawasan_id': kid, 'kabupaten': kab, 'tahun': th, 'produksi_ton': round(prod[th], 1), 'luas_panen_ha': round(luas[th], 1)})
    print(kid, sorted(set(luas) & set(prod)))
for kid, kab in [('temanggung','Temanggung'),('wonosobo','Wonosobo'),('magelang','Magelang'),('karanganyar','Karanganyar'),('tegal','Tegal')]:
    tambah(kid, kab, seri(3300, 2116, kab), seri(3300, 2118, kab, skala=0.1))
tambah('majalengka','Majalengka', seri(3200,174,'Majalengka'), seri(3200,176,'Majalengka', skala=0.1))
tambah('humbahas','Humbang Hasundutan', seri(1200,534,'Humbang'), seri(1200,541,'Humbang', skala=0.1))
import csv
from pathlib import Path
out = Path(__file__).resolve().parent.parent / "app" / "data" / "produktivitas_bps.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["kawasan_id", "kabupaten", "tahun", "produksi_ton", "luas_panen_ha"])
    w.writeheader()
    w.writerows(rows)
print(f"{len(rows)} baris disimpan ke {out}")

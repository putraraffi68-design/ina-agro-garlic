"""Laporan PDF hasil analisis kesesuaian lahan (F5 Unduh Laporan)."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from rule_engine import PARAM

WARNA = {"S1": "#1f7a3a", "S2": "#7a9a1f", "S3": "#c27c0e", "N": "#b3261e"}


def buat_pdf(h):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title=f"Laporan Kesesuaian Lahan {h['analysis_id']}")
    ss = getSampleStyleSheet()
    kecil = ParagraphStyle("kecil", parent=ss["Normal"], fontSize=8.5, textColor=colors.grey)
    el = []
    lok = h["lokasi"]
    el.append(Paragraph("INA Agro-GARLIC — Laporan Kesesuaian Lahan Bawang Putih", ss["Title"]))
    el.append(Paragraph(
        f"ID analisis: {h['analysis_id']} · Dibuat: {h.get('waktu', '-')}", kecil))
    el.append(Spacer(1, 10))
    el.append(Paragraph(
        f"<b>Lokasi:</b> Desa {lok.get('desa', '-')}, Kec. {lok.get('kecamatan', '-')}, "
        f"Kab. {lok.get('kabupaten', '-')} ({lok['lat']:.5f}, {lok['lon']:.5f})", ss["Normal"]))
    el.append(Spacer(1, 8))
    warna = colors.HexColor(WARNA[h["kelas_akhir"]])
    el.append(Paragraph(
        f"<font size=22 color='{WARNA[h['kelas_akhir']]}'><b>{h['kelas_akhir']}</b></font>"
        f"&nbsp;&nbsp;<font size=14><b>{h['label']}</b></font>",
        ParagraphStyle("kelas", parent=ss["Normal"], leading=28)))
    el.append(Spacer(1, 10))
    el.append(Paragraph(h["penjelasan"], ss["Normal"]))
    el.append(Paragraph(f"Kelengkapan data: {h['kelengkapan_data']}", kecil))
    el.append(Spacer(1, 12))

    el.append(Paragraph("Rincian per parameter", ss["Heading3"]))
    rows = [["Parameter", "Nilai", "Ideal (S1)", "Kelas", "Sumber"]]
    for k, d in h["kelas_per_parameter"].items():
        sat = d.get("satuan") or ""
        nilai = f"{d['nilai']} {sat}".strip()
        if d.get("dekat_ambang"):
            nilai += " *"
        rows.append([PARAM[k]["label"], nilai, d["ideal"], d["kelas"], d["sumber"]])
    t = Table(rows, colWidths=[4 * cm, 3.4 * cm, 3.6 * cm, 1.6 * cm, 3.4 * cm])
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
             ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
             ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
             ("FONTSIZE", (0, 0), (-1, -1), 9.5)]
    for i, (k, d) in enumerate(h["kelas_per_parameter"].items(), start=1):
        if k in h.get("faktor_pembatas_kode", []):
            style.append(("TEXTCOLOR", (0, i), (-1, i), warna))
            style.append(("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"))
    t.setStyle(TableStyle(style))
    el.append(t)
    if h.get("parameter_dekat_ambang"):
        el.append(Paragraph("* nilai dekat ambang batas kelas", kecil))
    if h.get("parameter_hilang"):
        el.append(Paragraph("Data tidak tersedia: " + ", ".join(h["parameter_hilang"]), kecil))
    el.append(Spacer(1, 12))

    pp = h.get("prediksi_panen")
    if pp:
        el.append(Paragraph("Prediksi hasil panen (model ML Random Forest)", ss["Heading3"]))
        el.append(Paragraph(
            f"<b>{pp['ton_per_ha']:g} ton/ha</b> (rentang {pp['rentang_ton_per_ha'][0]:g}–{pp['rentang_ton_per_ha'][1]:g} ton/ha; "
            f"rata-rata sentra {pp.get('rerata_sentra_ton_per_ha')} ton/ha; galat rata-rata model ±{pp.get('mae_ton_per_ha')} ton/ha)", ss["Normal"]))
        el.append(Paragraph(pp["catatan"], kecil))
        el.append(Spacer(1, 10))
    el.append(Paragraph("Rekomendasi", ss["Heading3"]))
    for r in h["rekomendasi"]:
        el.append(Paragraph("• " + r, ss["Normal"]))
    el.append(Spacer(1, 14))
    if h.get("perlu_verifikasi_lapangan"):
        el.append(Paragraph("<b>Disarankan verifikasi lapangan oleh penyuluh</b> (data tidak lengkap "
                            "atau ada nilai dekat ambang batas).", ss["Normal"]))
    el.append(Spacer(1, 10))
    el.append(Paragraph(
        "Metode: sistem pakar rule-based (FAO 1976 / juknis BBSDLP, disederhanakan). Kelas akhir = "
        "kelas terburuk dari semua parameter (hukum minimum). Prototipe: data spasial masih data "
        "contoh dan ambang kriteria belum dikalibrasi pakar.", kecil))
    doc.build(el)
    return buf.getvalue()

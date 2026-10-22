"""Pembuat laporan kepatuhan: CSV dan PDF (ReportLab). Murni format, tanpa akses database."""
import csv
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HEAD = ["ID", "Waktu", "Kamera", "Track ID", "Jenis Pelanggaran", "Tanpa Helm", "Tanpa Safety Vest", "File Snapshot"]


def to_csv(rows) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(HEAD)
    for r in rows:
        w.writerow([r.id, r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), r.camera, r.track_id or "-", r.jenis,
                    "Ya" if r.missing_helmet else "Tidak", "Ya" if r.missing_vest else "Tidak", r.snapshot])
    return "\ufeff" + buf.getvalue()          # BOM agar terbaca benar di Excel


def _table(data, widths, header_color="#1e3a5f"):
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6fa")]),
    ]))
    return t


def to_pdf(summary: dict, rows, max_rows: int = 500) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm,
                            bottomMargin=1.5 * cm, title="Laporan Kepatuhan APD")
    st = getSampleStyleSheet()
    rate = summary["compliance_rate"]
    el = [Paragraph("Laporan Kepatuhan Penggunaan APD", st["Title"]),
          Paragraph(f"Periode: {summary['start']} s.d. {summary['end']} &nbsp;|&nbsp; Dibuat: "
                    f"{datetime.now():%Y-%m-%d %H:%M}", st["Normal"]), Spacer(1, 10),
          _table([["Ringkasan", "Nilai"], ["Total pelanggaran", summary["total"]],
                  ["Tingkat kepatuhan", f"{rate}%" if rate is not None else "belum ada data"]], [8 * cm, 5 * cm]),
          Spacer(1, 10), Paragraph("Pelanggaran per jenis", st["Heading3"])]
    el.append(_table([["Jenis", "Jumlah"]] + [[k, v] for k, v in summary["by_type"].items()] or [["-", 0]], [8 * cm, 5 * cm]))
    el += [Spacer(1, 10), Paragraph("Daftar pelanggaran", st["Heading3"])]
    data = [["Waktu", "Kamera", "Track", "Jenis pelanggaran"]]
    data += [[r.timestamp.strftime("%Y-%m-%d %H:%M:%S"), r.camera, r.track_id or "-", r.jenis] for r in rows[:max_rows]]
    el.append(_table(data, [4.2 * cm, 3 * cm, 2 * cm, 7 * cm]))
    if len(rows) > max_rows:
        el.append(Paragraph(f"... {len(rows) - max_rows} baris lainnya hanya tersedia pada ekspor CSV.", st["Italic"]))
    doc.build(el)
    return buf.getvalue()

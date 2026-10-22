"""Uji unit backend: keamanan (hash password, token) dan ekspor laporan CSV/PDF. (Bagian: Achlaken - Backend)
Jalankan: pytest tests/test_backend_unit.py -v"""
from app import security
from app.reports import to_csv, to_pdf

def test_password_dan_token():
    h = security.hash_password("rahasia")
    assert security.verify_password("rahasia", h) and not security.verify_password("salah", h)
    tok = security.make_token("admin")
    assert security.read_token(tok) == "admin"
    assert security.read_token(tok[:-2] + "xx") is None and security.read_token(None) is None


def test_laporan_csv_pdf():
    from types import SimpleNamespace as NS
    from datetime import datetime
    rows = [NS(id=1, timestamp=datetime(2026, 10, 16, 9, 5), camera="demo", track_id=2, jenis="Tanpa Helm",
               missing_helmet=True, missing_vest=False, snapshot="a.jpg")]
    summary = {"start": "2026-10-10", "end": "2026-10-16", "total": 1, "compliance_rate": 66.7,
               "by_type": {"Tanpa Helm": 1}, "per_day": [{"date": "2026-10-16", "count": 1}]}
    csv_text = to_csv(rows)
    assert "Tanpa Helm" in csv_text and csv_text.startswith("\ufeff")
    assert to_pdf(summary, rows)[:4] == b"%PDF"

"""Uji fungsional API (butuh: pip install -r requirements.txt). Jalankan: pytest -v"""
import tempfile
import time

from app import config  # noqa: E402

config.DB_URL = f"sqlite:///{tempfile.mkdtemp()}/test.db"   # database sementara, sebelum app.main di-import
config.COOLDOWN = 30

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_alur_lengkap():
    with TestClient(app) as c:
        # FR-08: tanpa login ditolak, login salah ditolak
        assert c.get("/api/stats").status_code == 401
        assert c.post("/api/auth/login", json={"username": "admin", "password": "salah"}).status_code == 401
        assert c.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 200

        # FR-01..03: sumber demo berjalan dan menilai kepatuhan
        assert c.post("/api/source/start", json={"kind": "demo"}).status_code == 200
        time.sleep(3)
        s = c.get("/api/stats").json()
        assert s["running"] and s["workers"] == 3 and s["violations"] == 2

        # FR-05/06: pelanggaran tersimpan dan dapat difilter
        d = c.get("/api/violations").json()
        assert d["total"] == 2
        assert {i["jenis"] for i in d["items"]} == {"Tanpa Helm", "Tanpa Safety Vest"}
        assert c.get("/api/violations?jenis=Tanpa Helm").json()["total"] == 1
        assert c.get(d["items"][0]["snapshot_url"]).headers["content-type"] == "image/jpeg"

        # FR-07: laporan dan ekspor
        assert c.get("/api/reports/summary").json()["total"] == 2
        assert "Tanpa Helm" in c.get("/api/reports/export?format=csv").text
        assert c.get("/api/reports/export?format=pdf").content[:4] == b"%PDF"

        c.post("/api/source/stop")
        assert c.get("/api/stats").json()["running"] is False

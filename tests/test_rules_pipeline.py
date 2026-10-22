"""Uji aturan kepatuhan, pipeline real-time, dan pesan error model. (Bagian: Fauzan - AI/ML)
Jalankan: pytest tests/test_rules_pipeline.py -v"""
import time

from app import config
from app.pipeline import Pipeline
from app.rules import Det, canonical, evaluate

P = (100, 100, 150, 220)  # kotak pekerja (tinggi 120)
HELM = Det("helmet", 0.9, (105, 100, 145, 120))
VEST = Det("vest", 0.9, (102, 140, 148, 190))


def test_canonical_class_names():
    assert canonical("NO-Hardhat") == "no_helmet"
    assert canonical("Safety Vest") == "vest"
    assert canonical("Hardhat") == "helmet"
    assert canonical("machinery") is None


def test_skenario_apd_lengkap():
    w = evaluate([Det("person", .9, P), HELM, VEST])[0]
    assert w.compliant and w.violation is None


def test_skenario_tanpa_helm():
    w = evaluate([Det("person", .9, P), VEST])[0]
    assert not w.compliant and w.violation == "Tanpa Helm"


def test_skenario_tanpa_vest():
    w = evaluate([Det("person", .9, P), HELM])[0]
    assert w.violation == "Tanpa Safety Vest"


def test_tanpa_keduanya_dan_kelas_no():
    assert evaluate([Det("person", .9, P)])[0].violation == "Tanpa Helm & Vest"
    nh = Det("no_helmet", 0.8, (105, 100, 145, 120))
    assert evaluate([Det("person", .9, P), nh, VEST])[0].violation == "Tanpa Helm"


def test_helm_pekerja_lain_tidak_dihitung():
    far = Det("helmet", .9, (400, 100, 440, 120))
    assert evaluate([Det("person", .9, P), far, VEST])[0].violation == "Tanpa Helm"


class FakeSink:
    def __init__(self):
        self.violations, self.samples = [], []

    def log_violation(self, **kw):
        self.violations.append(kw)

    def log_sample(self, *a):
        self.samples.append(a)


def test_pipeline_demo_mencatat_pelanggaran_sekali():
    config.COOLDOWN, config.SAMPLE_EVERY = 30, 0.5
    sink = FakeSink()
    p = Pipeline(sink)
    p.start("demo")
    time.sleep(2.5)
    state, jpeg = dict(p.state), p.jpeg
    p.stop()
    jenis = sorted(v["jenis"] for v in sink.violations)
    assert jenis == ["Tanpa Helm", "Tanpa Safety Vest"], jenis        # pekerja #1 patuh -> tidak dicatat
    assert state["workers"] == 3 and state["compliant"] == 1 and state["violations"] == 2
    assert jpeg and jpeg[:2] == b"\xff\xd8" and sink.samples
    assert state["fps"] >= 10, state


def test_model_tidak_ada_memberi_pesan_jelas():
    config.MODEL_PATH = "/tidak/ada/best.pt"
    try:
        Pipeline(FakeSink()).start("webcam")
        raise AssertionError("seharusnya error")
    except RuntimeError as e:
        assert "Model YOLO tidak ditemukan" in str(e)

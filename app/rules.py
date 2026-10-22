"""Aturan kepatuhan APD. Murni Python (tanpa YOLO/DB) sehingga mudah diuji.

Pekerja PATUH jika helm DAN safety vest terdeteksi pada pekerja tersebut.
Helm dicari di area kepala (bagian atas kotak pekerja), vest di area badan.
Jika dataset punya kelas 'NO-Hardhat' / 'NO-Safety Vest', kelas itu dipakai sebagai bukti tambahan.
"""
import re
from dataclasses import dataclass

V_HELMET = "Tanpa Helm"
V_VEST = "Tanpa Safety Vest"
V_BOTH = "Tanpa Helm & Vest"
VIOLATION_TYPES = [V_HELMET, V_VEST, V_BOTH]

# Nama kelas dataset dinormalisasi (huruf kecil, tanpa spasi/simbol) lalu dipetakan ke kelas standar.
ALIASES = {
    "person": {"person", "worker", "pekerja", "people"},
    "helmet": {"helmet", "hardhat", "hardhats", "safetyhelmet", "helm"},
    "vest": {"vest", "safetyvest", "hivisvest", "highvisibilityvest", "rompi"},
    "no_helmet": {"nohelmet", "nohardhat", "nosafetyhelmet", "nohelm"},
    "no_vest": {"novest", "nosafetyvest", "norompi"},
}
_LOOKUP = {alias: key for key, names in ALIASES.items() for alias in names}

HEAD_REGION = (-0.05, 0.40)   # helm: pusat kotak berada di 40% teratas pekerja
BODY_REGION = (0.10, 0.80)    # vest: pusat kotak berada di badan pekerja


def canonical(name) -> str | None:
    return _LOOKUP.get(re.sub(r"[^a-z0-9]", "", str(name).lower()))


@dataclass
class Det:
    label: str            # kelas standar: person/helmet/vest/no_helmet/no_vest
    conf: float
    box: tuple            # (x1, y1, x2, y2) piksel
    track_id: int | None = None


@dataclass
class Worker:
    box: tuple
    track_id: int | None
    has_helmet: bool
    has_vest: bool

    @property
    def compliant(self) -> bool:
        return self.has_helmet and self.has_vest

    @property
    def violation(self) -> str | None:
        if self.compliant:
            return None
        if not self.has_helmet and not self.has_vest:
            return V_BOTH
        return V_HELMET if not self.has_helmet else V_VEST


def _score(dets, label, person_box, region) -> float:
    x1, y1, x2, y2 = person_box
    h = y2 - y1
    top, bottom = y1 + region[0] * h, y1 + region[1] * h
    best = 0.0
    for d in dets:
        if d.label != label:
            continue
        cx, cy = (d.box[0] + d.box[2]) / 2, (d.box[1] + d.box[3]) / 2
        if x1 <= cx <= x2 and top <= cy <= bottom:
            best = max(best, d.conf)
    return best


def evaluate(dets) -> list[Worker]:
    """Ubah daftar deteksi satu frame menjadi status kepatuhan tiap pekerja."""
    workers = []
    for p in (d for d in dets if d.label == "person"):
        helmet = _score(dets, "helmet", p.box, HEAD_REGION)
        no_helmet = _score(dets, "no_helmet", p.box, HEAD_REGION)
        vest = _score(dets, "vest", p.box, BODY_REGION)
        no_vest = _score(dets, "no_vest", p.box, BODY_REGION)
        workers.append(Worker(p.box, p.track_id, helmet > no_helmet, vest > no_vest))
    return workers

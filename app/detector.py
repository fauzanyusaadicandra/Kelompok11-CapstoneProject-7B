"""Detektor YOLO (Ultralytics) dan adegan sintetis untuk mode demo tanpa model."""
import math

import cv2
import numpy as np

from .rules import Det, canonical


class YoloDetector:
    def __init__(self, model_path: str, conf: float, imgsz: int):
        from ultralytics import YOLO  # import di sini agar mode demo tidak butuh ultralytics
        self.model = YOLO(model_path)
        self.conf, self.imgsz = conf, imgsz
        self.names = self.model.names
        self.tracking = True

    def detect(self, frame) -> list[Det]:
        kw = dict(conf=self.conf, imgsz=self.imgsz, verbose=False)
        try:
            r = (self.model.track(frame, persist=True, **kw) if self.tracking else self.model.predict(frame, **kw))[0]
        except Exception:                      # tracker tidak tersedia -> pakai deteksi biasa
            self.tracking = False
            r = self.model.predict(frame, **kw)[0]
        out = []
        b = r.boxes
        if b is None or len(b) == 0:
            return out
        xyxy, conf, cls = b.xyxy.cpu().numpy(), b.conf.cpu().numpy(), b.cls.cpu().numpy()
        ids = b.id.cpu().numpy() if getattr(b, "id", None) is not None else [None] * len(cls)
        for i in range(len(cls)):
            label = canonical(self.names[int(cls[i])])
            if label:
                out.append(Det(label, float(conf[i]), tuple(float(v) for v in xyxy[i]),
                               int(ids[i]) if ids[i] is not None else None))
        return out


class SyntheticScene:
    """Adegan simulasi 3 pekerja (lengkap / tanpa helm / tanpa vest) untuk demo dan pengujian."""
    W, H = 640, 360
    WORKERS = [(1, True, True, 90, 120, 0.9), (2, False, True, 320, 150, 0.7), (3, True, False, 500, 110, 1.1)]

    def render(self, idx: int):
        img = np.full((self.H, self.W, 3), (189, 164, 138), np.uint8)       # langit
        cv2.rectangle(img, (0, 60), (self.W, 200), (139, 116, 100), -1)      # bangunan
        for i in range(6):
            cv2.rectangle(img, (30 + i * 105, 80), (100 + i * 105, 180), (184, 163, 148), -1)
        cv2.rectangle(img, (0, 270), (self.W, self.H), (158, 168, 168), -1)   # tanah
        dets, t = [], idx / 15.0
        for tid, helm, vest, bx, by, sp in self.WORKERS:
            x, y = int(bx + 70 * math.sin(t * sp * 0.6)), by
            cv2.rectangle(img, (x + 8, y + 34), (x + 42, y + 84), (22, 115, 249) if vest else (139, 116, 100), -1)
            cv2.rectangle(img, (x + 10, y + 84), (x + 40, y + 120), (59, 41, 30), -1)
            cv2.circle(img, (x + 25, y + 22), 13, (165, 201, 241), -1)
            if helm:
                cv2.ellipse(img, (x + 25, y + 19), (14, 14), 0, 180, 360, (21, 204, 250), -1)
            dets.append(Det("person", 0.95, (x - 2, y + 2, x + 52, y + 124), tid))
            if helm:
                dets.append(Det("helmet", 0.9, (x + 9, y + 4, x + 41, y + 22), tid))
            if vest:
                dets.append(Det("vest", 0.9, (x + 8, y + 34, x + 42, y + 84), tid))
        return img, dets

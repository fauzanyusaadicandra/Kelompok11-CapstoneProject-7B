"""Evaluasi model terhadap target proyek: precision, recall, mAP@0.5 (>= 80%) dan FPS (>= 10).

    python train/evaluate.py --weights models/best.pt --data datasets/ppe/data.yaml --video demo.mp4
"""
import argparse
import time

import cv2
from ultralytics import YOLO

ap = argparse.ArgumentParser()
ap.add_argument("--weights", default="models/best.pt")
ap.add_argument("--data", required=True)
ap.add_argument("--split", default="test", help="test / val")
ap.add_argument("--video", help="video untuk mengukur FPS (opsional)")
ap.add_argument("--frames", type=int, default=150)
a = ap.parse_args()

model = YOLO(a.weights)
m = model.val(data=a.data, split=a.split, verbose=False).box
rows = [("Precision", m.mp), ("Recall", m.mr), ("mAP@0.5", m.map50), ("mAP@0.5:0.95", m.map)]
print("\n=== Metrik deteksi (data %s) ===" % a.split)
for name, v in rows:
    print(f"{name:14s}: {v * 100:5.1f}%  {'OK' if v >= 0.8 or name == 'mAP@0.5:0.95' else 'DI BAWAH TARGET 80%'}")
for i, n in model.names.items():
    print(f"  kelas {n:15s} AP50 = {m.ap50[list(m.ap_class_index).index(i)] * 100:5.1f}%" if i in m.ap_class_index else f"  kelas {n}: tidak ada di data")

if a.video:
    cap, n, t_total = cv2.VideoCapture(a.video), 0, 0.0
    while n < a.frames:
        ok, f = cap.read()
        if not ok:
            break
        t = time.time(); model.predict(f, imgsz=640, verbose=False); t_total += time.time() - t; n += 1
    if n:
        print(f"\n=== Kecepatan ===\n{n / t_total:.1f} FPS | {t_total / n * 1000:.0f} ms/frame  {'OK' if n / t_total >= 10 else 'DI BAWAH TARGET 10 FPS'}")

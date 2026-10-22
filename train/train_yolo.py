"""Fine-tuning YOLO (transfer learning) untuk deteksi pekerja, helm, dan safety vest.

Contoh (Google Colab / Kaggle, GPU aktif):
    pip install ultralytics
    python train/train_yolo.py --data /content/ppe/data.yaml --model yolov8s.pt --epochs 60
Hasil terbaik: runs/apd/weights/best.pt  ->  salin ke  models/best.pt
"""
import argparse

from ultralytics import YOLO

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True, help="path data.yaml (lihat train/data.yaml.example)")
ap.add_argument("--model", default="yolov8n.pt", help="yolov8n.pt (ringan) / yolov8s.pt (lebih akurat)")
ap.add_argument("--epochs", type=int, default=60)
ap.add_argument("--imgsz", type=int, default=640)
ap.add_argument("--batch", type=int, default=16)
ap.add_argument("--name", default="apd")
a = ap.parse_args()

model = YOLO(a.model)  # bobot pretrained COCO -> transfer learning
model.train(data=a.data, epochs=a.epochs, imgsz=a.imgsz, batch=a.batch, project="runs", name=a.name,
            patience=15, hsv_v=0.5, hsv_s=0.6, degrees=5, translate=0.1, scale=0.5, fliplr=0.5,  # augmentasi cahaya/sudut
            mosaic=1.0, blur=0.0)
print("\nSelesai. Salin runs/%s/weights/best.pt ke models/best.pt" % a.name)

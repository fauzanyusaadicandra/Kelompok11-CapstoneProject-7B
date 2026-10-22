# Model dan Dataset (Fauzan - AI/ML Engineer)

## 1. Tujuan
Model YOLO mendeteksi **Person**, **Helmet/Hardhat**, dan **Safety Vest** (opsional kelas `NO-Hardhat`, `NO-Safety Vest`). Status patuh ditentukan oleh `app/rules.py`: pekerja patuh jika helm **dan** vest terdeteksi pada pekerja tersebut.

## 2. Dataset
- Sumber publik: Roboflow Universe / Kaggle (format **YOLOv8**), mis. "Construction Site Safety" atau "PPE Detection". Catat nama, URL, lisensi, dan jumlah gambar yang dipakai.
- Data tambahan: video/gambar sendiri yang menyerupai area kerja (variasi cahaya, sudut kamera, jarak). Anotasi dibantu Iqbal.
- Pembagian: train / val / test (mis. 70 / 20 / 10). **Test set tidak dipakai saat training**; hanya untuk evaluasi akhir.
- Salin `train/data.yaml.example` menjadi `data.yaml`, lalu sesuaikan path dan nama kelas. Nama kelas dikenali otomatis (lihat `ALIASES` di `app/rules.py`).

| Item | Isi (lengkapi) |
|---|---|
| Nama dataset publik | |
| Jumlah gambar train / val / test | |
| Jumlah data tambahan sendiri | |
| Daftar kelas | |

## 3. Training (Google Colab / Kaggle, GPU)
```bash
pip install ultralytics
python train/train_yolo.py --data /content/ppe/data.yaml --model yolov8s.pt --epochs 60
```
Hasil: `runs/apd/weights/best.pt` -> salin ke `models/best.pt`. File `.pt` tidak di-commit (ada di `.gitignore`); bagikan lewat Google Drive atau GitHub Release.

## 4. Evaluasi terhadap target (NFR-02, NFR-06)
```bash
python train/evaluate.py --weights models/best.pt --data data.yaml --video video_uji.mp4
```
| Metrik | Target | Hasil | Keterangan |
|---|---|---|---|
| Precision | >= 80% | | |
| Recall | >= 80% | | |
| mAP@0.5 | >= 80% | | |
| FPS (laptop) | >= 10 | | |

## 5. Penyetelan bila hasil kurang
- Banyak helm/vest tidak terdeteksi -> turunkan `CONF` (mis. 0.3), tambah data dengan variasi cahaya dan sudut, coba `yolov8s`.
- Banyak false positive -> naikkan `CONF`, naikkan `MIN_FRAMES`.
- FPS rendah -> `yolov8n`, `IMGSZ=480`, `MAX_WIDTH=640`, atau pakai GPU.
- Posisi helm/vest dinilai terhadap kotak pekerja (`HEAD_REGION`, `BODY_REGION` di `app/rules.py`); sesuaikan bila kamera berada sangat tinggi/rendah.

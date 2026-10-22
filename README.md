# APD Monitor - Sistem Monitoring Kepatuhan APD Berbasis Computer Vision (YOLO)

**NEXUS AI - Kelompok 11 - Capstone Project 7B**
Fauzan Yusa Adicandra (AI/ML & koordinator) | Muhammad Achlaken Al-Hakim (backend & database) | Muhammad Iqbal Kurnia Adjie (frontend & QA)

Sistem menerima video / kamera real-time, mendeteksi **pekerja, helm, dan safety vest** dengan YOLO, menentukan status **patuh / tidak patuh**, menyimpan pelanggaran (waktu, jenis, snapshot bukti), lalu menampilkannya pada dashboard web beserta riwayat dan laporan (CSV/PDF). Implementasi ini mengikuti *Project Definition Document* (FR-01 s.d. FR-09, NFR-01 s.d. NFR-06).

```
Kamera/video -> OpenCV (frame) -> YOLO (pekerja, helm, vest) -> aturan kepatuhan -> SQLite + snapshot -> Dashboard web
                                                                                      (Live | Riwayat | Laporan CSV/PDF)
```

## 1. Prasyarat
- Python **3.10+** (disarankan 3.11/3.12), pip, Git
- Webcam / video uji (opsional untuk mode Demo)
- GPU tidak wajib (CPU cukup dengan model `yolov8n`); GPU dipakai otomatis oleh PyTorch bila tersedia

## 2. Instalasi dan menjalankan (cara tercepat)

**Windows:** klik dua kali `run.bat`  |  **Linux/macOS:** `./run.sh`
Skrip ini membuat virtual environment, memasang dependensi, lalu menjalankan server. Atau manual:

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   |  source .venv/bin/activate  (Linux/macOS)
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Buka **http://localhost:8000** -> login: **`admin` / `admin123`** (ubah lewat `ADMIN_USER`, `ADMIN_PASS`, `SECRET_KEY`).
Dokumentasi API otomatis (Swagger): **http://localhost:8000/docs**.

> Instalasi pertama mengunduh PyTorch (besar, beberapa menit). Jika hanya ingin mencoba dashboard, mode Demo (di bawah) sudah berjalan.

## 3. Tiga cara menjalankan deteksi

| Mode | Kapan dipakai | Langkah |
|---|---|---|
| **A. Demo (tanpa model)** | Mencoba dashboard / presentasi sebelum model siap | Dashboard -> sumber **Demo (tanpa model)** -> Mulai. Adegan simulasi 3 pekerja; deteksinya *disimulasikan* (bukan YOLO) tetapi seluruh alur setelahnya (aturan, database, riwayat, laporan) asli. Ditandai badge **MODE DEMO**. |
| **B. YOLO dengan model hasil latihan** | Penggunaan sebenarnya | Letakkan bobot di **`models/best.pt`** (atau set `MODEL_PATH`), lalu pilih Webcam / Unggah video / URL kamera. |
| **C. Latih model sendiri** | Belum punya `best.pt` | Lihat bagian 4. |

## 4. Melatih model YOLO (tugas Fauzan - Google Colab / Kaggle)
1. **Dataset**: unduh dataset PPE dari Roboflow Universe / Kaggle (mis. "Construction Site Safety", "PPE detection") dalam format **YOLOv8**. Pastikan ada kelas **Person**, **Hardhat/Helmet**, dan **Safety Vest** (kelas `NO-Hardhat` / `NO-Safety Vest` dipakai sebagai bukti tambahan jika ada). Tambahkan data sendiri bila memungkinkan (risiko #1 di dokumen).
2. Salin `train/data.yaml.example` -> `data.yaml`, sesuaikan path dan nama kelas.
3. Di Colab (Runtime -> GPU):
   ```bash
   !pip install ultralytics
   !python train/train_yolo.py --data /content/ppe/data.yaml --model yolov8s.pt --epochs 60
   ```
4. Unduh `runs/apd/weights/best.pt` -> simpan sebagai `models/best.pt` di proyek ini.
5. **Evaluasi terhadap target proyek** (precision, recall, mAP@0.5 >= 80%; FPS >= 10):
   ```bash
   python train/evaluate.py --weights models/best.pt --data data.yaml --video video_uji.mp4
   ```
   Hasilnya langsung menandai `OK` / `DI BAWAH TARGET`, dan dapat dimasukkan ke laporan/presentasi.

Nama kelas dikenali otomatis (tidak peka huruf besar/kecil, spasi, tanda `-`), lihat `app/rules.py`. Bila nama kelas dataset Anda berbeda, tambahkan ke `ALIASES`.

## 5. Cara memakai dashboard
1. **Live Monitoring** -> pilih sumber -> **Mulai**: video dengan kotak hijau (*Patuh*) / merah (*Tanpa Helm*, *Tanpa Safety Vest*, *Tanpa Helm & Vest*), kartu jumlah pekerja/patuh/pelanggaran, FPS & delay, dan **notifikasi** pelanggaran baru (FR-09).
   - *Webcam*: isi indeks kamera (0 = bawaan laptop).
   - *Unggah file video*: mp4/avi/mov/mkv/webm; diputar berulang sesuai FPS aslinya.
   - *Kamera smartphone/IP*: pakai aplikasi seperti "IP Webcam", isi URL mis. `http://192.168.1.5:8080/video` (satu jaringan Wi-Fi).
2. **Riwayat Pelanggaran**: filter tanggal & jenis, klik thumbnail untuk melihat snapshot bukti.
3. **Laporan Kepatuhan**: pilih periode -> ringkasan, grafik per hari & per jenis, **Ekspor CSV / PDF**.

Pelanggaran dicatat jika bertahan >= `MIN_FRAMES` frame (anti-kedip) dan tidak dicatat ulang untuk pekerja & jenis yang sama selama `COOLDOWN` detik (default 30).

## 6. Konfigurasi (environment variable)
| Variabel | Default | Fungsi |
|---|---|---|
| `MODEL_PATH` | `models/best.pt` | lokasi bobot YOLO |
| `CONF` / `IMGSZ` | `0.4` / `640` | threshold confidence / ukuran input inferensi |
| `MAX_WIDTH` | `960` | frame lebih lebar diperkecil (menaikkan FPS) |
| `MIN_FRAMES` / `COOLDOWN` | `5` / `30` | anti-kedip / jeda pencatatan ulang (detik) |
| `DB_URL` | SQLite `data/apd.db` | ganti ke PostgreSQL bila perlu |
| `ADMIN_USER` / `ADMIN_PASS` / `SECRET_KEY` | `admin` / `admin123` / (contoh) | **ganti sebelum dipakai di jaringan** |

Contoh Windows PowerShell: `$env:CONF="0.5"; python -m uvicorn app.main:app`

## 7. Struktur proyek
```
app/main.py       REST API + autentikasi + penyajian dashboard (FastAPI)
app/pipeline.py   loop real-time: frame -> YOLO -> aturan -> catat pelanggaran -> stream MJPEG
app/rules.py      aturan kepatuhan (helm di area kepala, vest di area badan) - mudah diuji
app/detector.py   wrapper YOLO (Ultralytics, tracking ByteTrack) + adegan Demo
app/database.py   model SQLite: users, violations, stat_logs
app/crud.py       query riwayat & ringkasan laporan
app/reports.py    ekspor CSV & PDF (ReportLab)
app/security.py   hash password PBKDF2 + token sesi HMAC
app/static/       dashboard (HTML, Bootstrap, Chart.js, JavaScript)
train/            train_yolo.py, evaluate.py, data.yaml.example
tests/            test_core.py (aturan, keamanan, pipeline), test_api.py (uji fungsional)
data/             apd.db, snapshots/, uploads/  (dibuat otomatis)
```

## 8. Pengujian
```bash
pytest -v
```
`test_core.py` menguji tiga skenario wajib (APD lengkap, tanpa helm, tanpa vest), keamanan, pipeline, serta ekspor CSV/PDF. `test_api.py` menguji alur login -> deteksi -> riwayat -> laporan secara end-to-end (mode Demo).

## 9. Pemetaan ke dokumen perancangan
| Kebutuhan | Implementasi |
|---|---|
| FR-01 input video & kamera real-time | `/api/source/*`: webcam, unggah file, URL kamera (+ Demo) |
| FR-02/03 deteksi & status patuh | `detector.py`, `rules.py`, `pipeline.py` (bounding box + label) |
| FR-04 dashboard | tab Live Monitoring |
| FR-05/06 simpan & riwayat pelanggaran | tabel `violations` + snapshot, tab Riwayat dengan filter |
| FR-07 laporan CSV/PDF | `reports.py`, tab Laporan |
| FR-08 login | cookie sesi bertanda tangan; seluruh `/api/*` terproteksi |
| FR-09 notifikasi (tambahan) | panel notifikasi + penanda BARU |
| NFR-01 keamanan | password ter-hash PBKDF2, endpoint wajib login, data disimpan lokal |
| NFR-02 performa | FPS & delay ditampilkan live dan dibandingkan target (>=10 FPS, <=3 dtk) |
| NFR-06 akurasi >= 80% | `train/evaluate.py` |

## 10. Pemecahan masalah
- **"Model YOLO tidak ditemukan"** -> belum ada `models/best.pt`; latih model (bagian 4) atau pakai mode Demo.
- **Webcam tidak terbuka** -> coba indeks 1, tutup aplikasi lain yang memakai kamera, izinkan akses kamera di OS.
- **FPS rendah** -> pakai `yolov8n`, turunkan `MAX_WIDTH`/`IMGSZ` (mis. 480), gunakan GPU.
- **Banyak false positive/negative** -> sesuaikan `CONF`, tambah data latih (variasi cahaya, sudut kamera), naikkan `MIN_FRAMES`.
- **Dashboard kosong/tanpa grafik** -> halaman memuat Bootstrap & Chart.js dari CDN, butuh internet saat pertama dibuka.

## 11. Batasan (sesuai scope)
Hanya helm dan safety vest; tanpa integrasi CCTV industri, absensi/identitas pekerja, dan analisis risiko. Bila model tidak menyediakan ID tracking, beberapa pekerja dengan jenis pelanggaran sama dihitung sebagai satu pada pencatatan. Tingkat kepatuhan pada laporan dihitung dari cuplikan jumlah pekerja tiap 5 detik. Nilai `SECRET_KEY` dan password bawaan wajib diganti bila diakses lewat jaringan.

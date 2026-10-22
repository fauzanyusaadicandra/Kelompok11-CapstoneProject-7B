# Rencana dan Hasil Pengujian Fungsional (Iqbal - Frontend & QA)

Kolom **Hasil aktual** dan **Status** sengaja dikosongkan: isi saat pengujian benar-benar dijalankan, lengkap dengan tanggal, penguji, dan bukti (screenshot di `docs/bukti/`).

## 1. Pengujian otomatis
```bash
pytest -v
```
Mencakup aturan 3 skenario, pipeline, keamanan, laporan CSV/PDF (`tests/test_rules_pipeline.py`, `tests/test_backend_unit.py`) dan alur API login -> deteksi -> riwayat -> laporan (`tests/test_api.py`, mode Demo).

## 2. Pengujian manual (checklist)
| ID | Kebutuhan | Langkah uji | Hasil yang diharapkan | Hasil aktual | Status |
|---|---|---|---|---|---|
| TC-01 | FR-01 | Unggah file video, klik Mulai | Video tampil di live feed | | |
| TC-02 | FR-01 | Pilih webcam, klik Mulai | Stream kamera tampil | | |
| TC-03 | FR-02/03 | Skenario APD lengkap | Kotak hijau berlabel Patuh | | |
| TC-04 | FR-02/03 | Skenario tanpa helm | Kotak merah "Tanpa Helm" | | |
| TC-05 | FR-02/03 | Skenario tanpa safety vest | Kotak merah "Tanpa Safety Vest" | | |
| TC-06 | FR-04 | Lihat kartu statistik saat deteksi | Jumlah pekerja, patuh, pelanggaran sesuai video | | |
| TC-07 | FR-05 | Setelah TC-04/05, cek Riwayat | Pelanggaran tersimpan dengan waktu, jenis, snapshot | | |
| TC-08 | FR-06 | Filter tanggal dan jenis | Tabel hanya menampilkan data sesuai filter | | |
| TC-09 | FR-07 | Laporan -> Ekspor CSV | File terunduh, dapat dibuka di Excel | | |
| TC-10 | FR-07 | Laporan -> Ekspor PDF | File PDF terunduh dan terbaca | | |
| TC-11 | FR-08 | Buka dashboard tanpa login / password salah | Ditolak; data tidak tampil | | |
| TC-12 | FR-09 | Saat pelanggaran terjadi | Notifikasi muncul dengan penanda BARU | | |
| TC-13 | NFR-02 | Amati kartu FPS/Delay selama deteksi YOLO | >= 10 FPS dan delay <= 3 dtk | | |
| TC-14 | NFR-03 | Hitung klik dari dashboard ke status, riwayat, laporan | Maksimal 3 klik | | |
| TC-15 | NFR-04 | Jalankan deteksi 30 menit | Tidak crash; jumlah pelanggaran di riwayat sesuai yang muncul | | |
| TC-16 | NFR-05 | Buka di Chrome, Edge, Firefox, dan layar ponsel | Tampilan dan fungsi normal | | |
| TC-17 | NFR-06 | `python train/evaluate.py ...` | Precision, recall, mAP@0.5 >= 80% | | |

## 3. Urutan demo (3 skenario wajib)
1. Login -> Live Monitoring -> pilih video uji -> Mulai.
2. Tunjukkan pekerja berAPD lengkap (hijau, Patuh).
3. Tunjukkan pekerja tanpa helm, lalu tanpa vest (merah, notifikasi muncul).
4. Buka Riwayat Pelanggaran, filter jenis, buka snapshot.
5. Buka Laporan, tunjukkan grafik, ekspor CSV dan PDF.

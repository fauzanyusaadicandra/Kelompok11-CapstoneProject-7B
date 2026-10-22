# Skema Database (Achlaken - Backend)

SQLite (`data/apd.db`) lewat SQLAlchemy 2.0; ganti `DB_URL` untuk PostgreSQL. Tabel dibuat otomatis saat server start (`init_db`), dan akun awal dibuat dari `ADMIN_USER` / `ADMIN_PASS`.

## users
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | integer PK | |
| username | varchar(50) unik | |
| password_hash | varchar(300) | PBKDF2-SHA256, format `salt$hash` |
| role | varchar(30) | default `safety_officer` |

## violations
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | integer PK | |
| timestamp | datetime (index) | waktu lokal pelanggaran |
| camera | varchar(50) | sumber (demo/webcam/file/url) |
| track_id | integer null | ID pekerja dari tracker YOLO |
| jenis | varchar(30) (index) | Tanpa Helm / Tanpa Safety Vest / Tanpa Helm & Vest |
| missing_helmet, missing_vest | boolean | rincian APD yang tidak terdeteksi |
| snapshot | varchar(200) | nama file di `data/snapshots/` |

## stat_logs
Cuplikan tiap `SAMPLE_EVERY` detik (default 5) selama ada pekerja; dipakai menghitung tingkat kepatuhan.
| Kolom | Tipe |
|---|---|
| id, timestamp (index), camera | integer PK, datetime, varchar |
| workers, compliant, violating | integer |

Tingkat kepatuhan = `SUM(compliant) / SUM(workers)` pada periode laporan.

## Relasi
Tidak ada foreign key (prototype): `violations` dan `stat_logs` berdiri sendiri; `users` hanya untuk login.

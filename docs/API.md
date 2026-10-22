# Dokumentasi REST API (Achlaken - Backend)

Base URL: `http://localhost:8000`. Swagger interaktif: `/docs`.
Autentikasi memakai cookie `apd_token` (httponly) dari `/api/auth/login`. Semua `/api/*` selain `/api/auth/login` dan `/api/auth/logout` memerlukan login (401 bila belum).

## Autentikasi
| Method | Endpoint | Body | Respons |
|---|---|---|---|
| POST | `/api/auth/login` | `{"username","password"}` | `{"username","role"}` + set cookie; 401 bila salah |
| POST | `/api/auth/logout` | - | `{"ok":true}` |
| GET | `/api/auth/me` | - | `{"username","role"}` |

## Sumber video dan deteksi
| Method | Endpoint | Keterangan |
|---|---|---|
| POST | `/api/source/start` | Body `{"kind":"demo\|webcam\|file\|url","value":...}`. `value`: indeks webcam / nama file hasil unggah / URL kamera. 400 + pesan jelas bila model/sumber tidak tersedia |
| POST | `/api/source/stop` | Hentikan pipeline |
| POST | `/api/source/upload` | `multipart/form-data` field `file` (mp4/avi/mov/mkv/webm) -> `{"file","original"}` |
| GET | `/api/stream` | Stream MJPEG video terdeteksi (untuk tag `<img>`); 409 bila belum berjalan |
| GET | `/api/stats` | `running, source, mode, fps, delay_ms, workers, compliant, violations, error, today_violations` |

## Riwayat pelanggaran
| Method | Endpoint | Query |
|---|---|---|
| GET | `/api/violations` | `date_from`, `date_to` (YYYY-MM-DD), `jenis`, `page`, `size` -> `{total, page, size, items[]}` |
| GET | `/api/violations/{id}/snapshot` | gambar JPEG bukti pelanggaran |

Nilai `jenis`: `Tanpa Helm`, `Tanpa Safety Vest`, `Tanpa Helm & Vest`.

## Laporan
| Method | Endpoint | Query |
|---|---|---|
| GET | `/api/reports/summary` | `start`, `end` (default 7 hari terakhir) -> `total, compliance_rate, by_type, per_day[]` |
| GET | `/api/reports/export` | `format=csv\|pdf`, `start`, `end` -> file unduhan |

## Kontrak dengan pipeline (integrasi model)
`DBSink` di `app/main.py` dipanggil oleh `Pipeline` (Fauzan): `log_violation(camera, track_id, jenis, missing_helmet, missing_vest, frame)` menyimpan snapshot ke `data/snapshots/` dan baris ke tabel `violations`; `log_sample(camera, workers, compliant, violating)` mengisi `stat_logs` untuk tingkat kepatuhan.

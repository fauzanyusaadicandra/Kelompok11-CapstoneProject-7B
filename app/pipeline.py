"""Pipeline real-time: ambil frame -> deteksi -> aturan kepatuhan -> catat pelanggaran -> stream MJPEG."""
import platform
import threading
import time
from pathlib import Path

import cv2

from . import config
from .detector import SyntheticScene, YoloDetector
from .rules import evaluate

GREEN, RED = (60, 170, 20), (40, 40, 220)   # BGR


class Pipeline:
    """`sink` harus punya log_violation(...) dan log_sample(...) (lihat DBSink di main.py)."""

    def __init__(self, sink):
        self.sink = sink
        self.detector = None
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.jpeg, self.frame_no = None, 0
        self._streak, self._last = {}, {}
        self.state = self._idle_state()

    @staticmethod
    def _idle_state():
        return {"running": False, "source": None, "mode": None, "fps": 0.0, "delay_ms": 0.0,
                "workers": 0, "compliant": 0, "violations": 0, "error": None}

    # ---------- kontrol ----------
    def _get_detector(self):
        if self.detector is None:
            if not Path(config.MODEL_PATH).exists():
                raise RuntimeError(f"Model YOLO tidak ditemukan di '{config.MODEL_PATH}'. Latih model (lihat README) "
                                   "atau gunakan sumber 'Demo (tanpa model)'.")
            self.detector = YoloDetector(config.MODEL_PATH, config.CONF, config.IMGSZ)
        return self.detector

    @staticmethod
    def _open(kind, value):
        if kind == "webcam":
            idx = int(value or 0)
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW) if platform.system() == "Windows" else cv2.VideoCapture(idx)
        elif kind == "file":
            path = config.UPLOAD / Path(str(value)).name
            if not path.exists():
                raise RuntimeError("File video tidak ditemukan. Unggah ulang videonya.")
            cap = cv2.VideoCapture(str(path))
        elif kind == "url":
            if not value:
                raise RuntimeError("URL kamera belum diisi.")
            cap = cv2.VideoCapture(value)
        else:
            raise RuntimeError("Jenis sumber tidak dikenal.")
        if not cap.isOpened():
            raise RuntimeError("Sumber video/kamera tidak dapat dibuka.")
        return cap

    def start(self, kind: str, value=None):
        self.stop()
        scene = cap = None
        if kind == "demo":
            scene = SyntheticScene()
        else:
            self._get_detector()
            cap = self._open(kind, value)
        self._stop.clear()
        self._streak.clear()
        self._last.clear()
        self.state = dict(self._idle_state(), running=True, source=kind, mode="demo" if scene else "yolo")
        self._thread = threading.Thread(target=self._run, args=(kind, cap, scene), daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None
        with self._lock:
            self.jpeg = None
        self.state = self._idle_state()

    # ---------- loop utama ----------
    def _run(self, kind, cap, scene):
        paced = scene is not None or kind == "file"           # file/demo diputar sesuai FPS aslinya
        native = (cap.get(cv2.CAP_PROP_FPS) if cap else 15) or 25
        native = native if 1 < native < 120 else 25
        idx, fails, ema, last_sample = 0, 0, None, 0.0
        try:
            while not self._stop.is_set():
                t0 = time.time()
                if scene:
                    frame, dets = scene.render(idx)
                else:
                    ok, frame = cap.read()
                    if not ok:
                        fails += 1
                        if kind == "file" and fails < 3:       # video selesai -> ulang dari awal
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            self._streak.clear()
                            continue
                        raise RuntimeError("Video selesai atau koneksi kamera terputus.")
                    fails = 0
                    frame = self._resize(frame)
                    dets = self.detector.detect(frame)
                idx += 1
                workers = evaluate(dets)
                self._annotate(frame, workers)
                self._check(frame, workers, kind)
                ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                done = time.time()
                with self._lock:
                    self.jpeg, self.frame_no = buf.tobytes(), self.frame_no + 1
                comp = sum(w.compliant for w in workers)
                inst = 1.0 / max(done - t0, 1e-3)
                ema = inst if ema is None else 0.9 * ema + 0.1 * inst
                self.state.update(workers=len(workers), compliant=comp, violations=len(workers) - comp,
                                  fps=round(ema, 1), delay_ms=round((done - t0) * 1000, 1))
                if workers and done - last_sample >= config.SAMPLE_EVERY:
                    last_sample = done
                    self.sink.log_sample(kind, len(workers), comp, len(workers) - comp)
                if paced:
                    time.sleep(max(0.0, 1.0 / native - (time.time() - t0)))
        except Exception as e:                                  # tampilkan penyebab ke dashboard
            self.state["error"] = str(e)
        finally:
            if cap:
                cap.release()
            self.state["running"] = False

    # ---------- bantu ----------
    @staticmethod
    def _resize(frame):
        h, w = frame.shape[:2]
        if w > config.MAX_WIDTH:
            return cv2.resize(frame, (config.MAX_WIDTH, int(h * config.MAX_WIDTH / w)))
        return frame

    @staticmethod
    def _annotate(frame, workers):
        for w in workers:
            x1, y1, x2, y2 = (int(v) for v in w.box)
            col = GREEN if w.compliant else RED
            label = "Patuh" if w.compliant else w.violation
            if w.track_id is not None:
                label = f"#{w.track_id} {label}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, max(y1 - th - 8, 0)), (x1 + tw + 6, max(y1, th + 8)), col, -1)
            cv2.putText(frame, label, (x1 + 3, max(y1 - 4, th + 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    def _check(self, frame, workers, camera):
        """Catat pelanggaran yang bertahan >= MIN_FRAMES frame, dengan jeda COOLDOWN per pekerja dan jenis."""
        now, seen = time.time(), set()
        for w in workers:
            if not w.violation:
                continue
            key = (w.track_id if w.track_id is not None else 0, w.violation)
            seen.add(key)
            self._streak[key] = self._streak.get(key, 0) + 1
            if self._streak[key] >= config.MIN_FRAMES and now - self._last.get(key, 0) >= config.COOLDOWN:
                self._last[key] = now
                self.sink.log_violation(camera=camera, track_id=w.track_id, jenis=w.violation,
                                        missing_helmet=not w.has_helmet, missing_vest=not w.has_vest, frame=frame)
        for k in list(self._streak):
            if k not in seen:
                self._streak[k] = 0

    def mjpeg(self):
        last = -1
        while self.state["running"]:
            with self._lock:
                no, jpg = self.frame_no, self.jpeg
            if jpg is not None and no != last:
                last = no
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            else:
                time.sleep(0.02)

"""REST API FastAPI + penyajian dashboard. Jalankan: uvicorn app.main:app --reload"""
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path

import cv2
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import config, crud, reports, security
from .database import SessionLocal, StatLog, User, Violation, get_db, init_db
from .pipeline import Pipeline
from .rules import VIOLATION_TYPES

STATIC = Path(__file__).parent / "static"


class DBSink:
    """Menyimpan pelanggaran (+ snapshot) dan cuplikan statistik ke database."""

    def log_violation(self, camera, track_id, jenis, missing_helmet, missing_vest, frame):
        name = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}.jpg"
        cv2.imwrite(str(config.SNAP / name), frame)
        with SessionLocal() as db:
            db.add(Violation(camera=camera, track_id=track_id, jenis=jenis, missing_helmet=missing_helmet,
                             missing_vest=missing_vest, snapshot=name))
            db.commit()

    def log_sample(self, camera, workers, compliant, violating):
        with SessionLocal() as db:
            db.add(StatLog(camera=camera, workers=workers, compliant=compliant, violating=violating))
            db.commit()


pipeline = Pipeline(DBSink())


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    pipeline.stop()


app = FastAPI(title="APD Monitor - NEXUS AI", description="Sistem monitoring kepatuhan APD berbasis YOLO", lifespan=lifespan)


# ---------------- autentikasi (FR-08) ----------------
def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    username = security.read_token(request.cookies.get(security.COOKIE))
    user = db.query(User).filter_by(username=username).first() if username else None
    if not user:
        raise HTTPException(401, "Belum login")
    return user


class LoginReq(BaseModel):
    username: str
    password: str


auth = APIRouter(prefix="/api/auth", tags=["auth"])


@auth.post("/login")
def login(req: LoginReq, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=req.username).first()
    if not user or not security.verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Username atau password salah")
    response.set_cookie(security.COOKIE, security.make_token(user.username), httponly=True, samesite="lax",
                        max_age=config.TOKEN_TTL)
    return {"username": user.username, "role": user.role}


@auth.post("/logout")
def logout(response: Response):
    response.delete_cookie(security.COOKIE)
    return {"ok": True}


@auth.get("/me")
def me(user: User = Depends(current_user)):
    return {"username": user.username, "role": user.role}


# ---------------- API terproteksi ----------------
api = APIRouter(prefix="/api", dependencies=[Depends(current_user)])


class StartReq(BaseModel):
    kind: str                 # demo | webcam | file | url
    value: str | None = None  # indeks webcam / nama file hasil unggah / URL kamera


@api.post("/source/start", tags=["source"])
def source_start(req: StartReq):
    if req.kind not in {"demo", "webcam", "file", "url"}:
        raise HTTPException(400, "kind harus demo, webcam, file, atau url")
    try:
        pipeline.start(req.kind, req.value)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(400, str(e))
    return pipeline.state


@api.post("/source/stop", tags=["source"])
def source_stop():
    pipeline.stop()
    return pipeline.state


@api.post("/source/upload", tags=["source"])
def source_upload(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
        raise HTTPException(400, "Format video harus mp4, avi, mov, mkv, atau webm")
    name = f"{uuid.uuid4().hex}{ext}"
    with open(config.UPLOAD / name, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"file": name, "original": file.filename}


@api.get("/stream", tags=["source"])
def stream():
    if not pipeline.state["running"]:
        raise HTTPException(409, "Belum ada sumber yang berjalan")
    return StreamingResponse(pipeline.mjpeg(), media_type="multipart/x-mixed-replace; boundary=frame")


@api.get("/stats", tags=["source"])
def stats(db: Session = Depends(get_db)):
    today = date.today()
    return dict(pipeline.state, today_violations=crud.violations_query(db, today, today).count())


@api.get("/violations", tags=["riwayat"])
def list_violations(date_from: str | None = None, date_to: str | None = None, jenis: str | None = None,
                    page: int = 1, size: int = 15, db: Session = Depends(get_db)):
    try:
        s, e = crud.parse_range(date_from or "2000-01-01", date_to)
    except ValueError as err:
        raise HTTPException(400, str(err))
    q = crud.violations_query(db, s, e, jenis)
    items = q.order_by(Violation.timestamp.desc()).offset((max(page, 1) - 1) * size).limit(size).all()
    return {"total": q.count(), "page": page, "size": size, "jenis_options": VIOLATION_TYPES,
            "items": [{"id": v.id, "timestamp": v.timestamp.isoformat(timespec="seconds"), "camera": v.camera,
                       "track_id": v.track_id, "jenis": v.jenis, "snapshot_url": f"/api/violations/{v.id}/snapshot"}
                      for v in items]}


@api.get("/violations/{vid}/snapshot", tags=["riwayat"])
def snapshot(vid: int, db: Session = Depends(get_db)):
    v = db.get(Violation, vid)
    path = config.SNAP / Path(v.snapshot).name if v else None
    if not path or not path.exists():
        raise HTTPException(404, "Snapshot tidak ditemukan")
    return FileResponse(path, media_type="image/jpeg")


def _range(start, end):
    try:
        return crud.parse_range(start, end)
    except ValueError as err:
        raise HTTPException(400, str(err))


@api.get("/reports/summary", tags=["laporan"])
def report_summary(start: str | None = None, end: str | None = None, db: Session = Depends(get_db)):
    return crud.build_summary(db, *_range(start, end))[0]


@api.get("/reports/export", tags=["laporan"])
def report_export(format: str = "csv", start: str | None = None, end: str | None = None, db: Session = Depends(get_db)):
    s, e = _range(start, end)
    summary, rows = crud.build_summary(db, s, e)
    fname = f"laporan_apd_{s}_{e}"
    if format == "csv":
        body, mime = reports.to_csv(rows).encode("utf-8"), "text/csv; charset=utf-8"
    elif format == "pdf":
        body, mime = reports.to_pdf(summary, rows), "application/pdf"
    else:
        raise HTTPException(400, "format harus csv atau pdf")
    return Response(body, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{fname}.{format}"'})


app.include_router(auth)
app.include_router(api)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")

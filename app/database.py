"""Model database (SQLAlchemy 2.0 + SQLite). Dapat dimigrasikan ke PostgreSQL lewat DB_URL."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from . import config
from .security import hash_password


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(30), default="safety_officer")


class Violation(Base):
    __tablename__ = "violations"
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.now)
    camera: Mapped[str] = mapped_column(String(50))
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    jenis: Mapped[str] = mapped_column(String(30), index=True)
    missing_helmet: Mapped[bool] = mapped_column(Boolean, default=False)
    missing_vest: Mapped[bool] = mapped_column(Boolean, default=False)
    snapshot: Mapped[str] = mapped_column(String(200))        # nama file di data/snapshots


class StatLog(Base):
    """Cuplikan jumlah pekerja per ~5 detik; dipakai menghitung tingkat kepatuhan pada laporan."""
    __tablename__ = "stat_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.now)
    camera: Mapped[str] = mapped_column(String(50))
    workers: Mapped[int] = mapped_column(Integer)
    compliant: Mapped[int] = mapped_column(Integer)
    violating: Mapped[int] = mapped_column(Integer)


engine = create_engine(config.DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.query(User).filter_by(username=config.ADMIN_USER).first():
            db.add(User(username=config.ADMIN_USER, password_hash=hash_password(config.ADMIN_PASS)))
            db.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

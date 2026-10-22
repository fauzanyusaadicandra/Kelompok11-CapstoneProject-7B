"""Query data untuk riwayat dan laporan."""
from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import func

from .database import StatLog, Violation
from .rules import VIOLATION_TYPES


def parse_range(start: str | None, end: str | None):
    """Rentang tanggal 'YYYY-MM-DD' (akhir inklusif). Default: 7 hari terakhir."""
    today = date.today()
    s = datetime.strptime(start, "%Y-%m-%d").date() if start else today - timedelta(days=6)
    e = datetime.strptime(end, "%Y-%m-%d").date() if end else today
    if e < s:
        raise ValueError("Tanggal akhir lebih awal dari tanggal awal")
    return s, e


def violations_query(db, s: date, e: date, jenis: str | None = None):
    q = db.query(Violation).filter(Violation.timestamp >= datetime.combine(s, datetime.min.time()),
                                   Violation.timestamp < datetime.combine(e + timedelta(days=1), datetime.min.time()))
    return q.filter(Violation.jenis == jenis) if jenis else q


def build_summary(db, s: date, e: date):
    rows = violations_query(db, s, e).order_by(Violation.timestamp.desc()).all()
    by_type = Counter(r.jenis for r in rows)
    by_day = Counter(r.timestamp.date() for r in rows)
    days = min((e - s).days + 1, 366)
    per_day = [{"date": (s + timedelta(days=i)).isoformat(), "count": by_day.get(s + timedelta(days=i), 0)}
               for i in range(days)]
    workers, compliant = db.query(func.coalesce(func.sum(StatLog.workers), 0), func.coalesce(func.sum(StatLog.compliant), 0)).filter(
        StatLog.timestamp >= datetime.combine(s, datetime.min.time()),
        StatLog.timestamp < datetime.combine(e + timedelta(days=1), datetime.min.time())).one()
    return {"start": s.isoformat(), "end": e.isoformat(), "total": len(rows),
            "compliance_rate": round(100 * compliant / workers, 1) if workers else None,
            "by_type": {t: by_type.get(t, 0) for t in VIOLATION_TYPES}, "per_day": per_day}, rows

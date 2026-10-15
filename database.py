"""SQLAlchemy models and database session configuration."""
import os
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'ddos.db'}")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class AttackSnapshot(Base):
    __tablename__ = "attack_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    fetched_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    source_timestamp = Column(String(80), nullable=True)
    attack_count = Column(Integer, nullable=False, default=0)
    payload_json = Column(Text, nullable=False)


Base.metadata.create_all(bind=engine)


def save_snapshot(payload, attack_count, source_timestamp=None):
    """Persist one successful upstream observation."""
    import json
    session = SessionLocal()
    try:
        row = AttackSnapshot(
            fetched_at=utc_now(),
            source_timestamp=source_timestamp,
            attack_count=attack_count,
            payload_json=json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
        )
        session.add(row)
        session.commit()
        return row.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_latest_snapshot():
    import json
    session = SessionLocal()
    try:
        row = session.query(AttackSnapshot).order_by(AttackSnapshot.id.desc()).first()
        if not row:
            return None
        return {
            "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
            "source_timestamp": row.source_timestamp,
            "attack_count": row.attack_count,
            "payload": json.loads(row.payload_json),
        }
    finally:
        session.close()

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for FastAPI routes to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    from backend import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _ensure_journal_tp_columns()
def _ensure_journal_tp_columns():
    """
    Lightweight schema upgrade for existing DBs:
    ensure journal_entries has TP columns used by the Log Trade form.
    """
    tp_columns = ("actual_tp1", "actual_tp2", "actual_tp3")

    with engine.begin() as conn:
        inspector = inspect(conn)
        if "journal_entries" not in inspector.get_table_names():
            return
        existing = {col["name"] for col in inspector.get_columns("journal_entries")}
        missing = [col for col in tp_columns if col not in existing]
        for col in missing:
            conn.execute(text(f"ALTER TABLE journal_entries ADD COLUMN {col} FLOAT"))

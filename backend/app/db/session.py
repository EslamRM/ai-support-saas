"""
Responsibility: SQLAlchemy engine/session factory for the API process.

Exposes get_db() for FastAPI's dependency injection. Celery workers do
NOT use this module -- they get their own session-maker in
workers/celery_app.py, because a request-scoped session (opened/closed
per HTTP request) is the wrong lifecycle for a long-lived worker process.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

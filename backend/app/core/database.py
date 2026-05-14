"""PostgreSQL engine and session factory (sync + async)."""
from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger(__name__)

# ── Sync engine (Alembic, seed, sync repositories) ───────────────────────────
sync_engine = create_engine(
    settings.postgres_dsn,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.app_env == "development",
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# ── Async engine (FastAPI endpoints) ─────────────────────────────────────────
async_engine = create_async_engine(
    settings.async_postgres_dsn,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Dependency helpers ────────────────────────────────────────────────────────

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def check_postgres_health() -> bool:
    try:
        async with AsyncSessionLocal() as s:
            await s.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        log.warning("PostgreSQL health check failed: %s", exc)
        return False

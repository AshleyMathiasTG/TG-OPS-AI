"""TG source database connection (MySQL, read-only).

In development with TGAP_FIXTURE_ONLY=1 the real MySQL is never touched;
fixture data is returned instead, allowing fully offline development.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger(__name__)

_FIXTURE_PATH = Path(__file__).parent.parent.parent.parent / "db" / "seeds" / "fixtures.json"


def _load_fixtures() -> Dict[str, Any]:
    if _FIXTURE_PATH.exists():
        with open(_FIXTURE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    log.warning("Fixture file not found at %s — returning empty dataset", _FIXTURE_PATH)
    return {}


class TGDatabase:
    """Thin wrapper around the TG MySQL source database."""

    def __init__(self) -> None:
        self._engine = None
        if not settings.tgap_fixture_only:
            self._init_engine()

    def _init_engine(self) -> None:
        try:
            from sqlalchemy import create_engine as _create
            self._engine = _create(
                settings.mysql_dsn,
                pool_pre_ping=True,
                connect_args={
                    "connect_timeout": settings.mysql_query_timeout_seconds,
                    "read_timeout": settings.mysql_query_timeout_seconds,
                },
            )
            log.info("TG MySQL engine initialised (%s:%s)", settings.db_host, settings.db_port)
        except Exception as exc:
            log.error("Failed to create TG MySQL engine: %s", exc)
            self._engine = None

    def execute_query(self, sql: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Execute a READ-ONLY SELECT query and return rows as list-of-dicts.

        Only SELECT statements are permitted against the TG source database.
        Any DML (INSERT/UPDATE/DELETE/DROP/TRUNCATE/ALTER) is rejected immediately.
        """
        if settings.tgap_fixture_only:
            log.debug("FIXTURE_ONLY mode — skipping real query")
            return []

        if self._engine is None:
            log.error("TG DB engine not available")
            return []

        # Enforce SELECT-only policy
        stripped = sql.strip().lstrip("(/").upper()
        first_word = stripped.split()[0] if stripped else ""
        if first_word not in ("SELECT", "WITH", "EXPLAIN"):
            log.error(
                "TG DB BLOCKED: Only SELECT queries allowed. Attempted: %s", first_word
            )
            raise PermissionError(
                f"TG Database is read-only. Only SELECT queries are permitted. "
                f"Got: {first_word}"
            )

        from sqlalchemy import text

        try:
            # Substitute %(key)s params into the SQL string directly
            # (SQLAlchemy text() uses :key syntax; LIMIT is not parameterisable
            # via prepared statements in most MySQL drivers)
            final_sql = sql
            if params:
                for k, v in params.items():
                    final_sql = final_sql.replace(f"%({k})s", str(int(v)))

            # Open a read-only transaction to guarantee no writes
            with self._engine.connect() as conn:
                conn.execute(text("SET SESSION TRANSACTION READ ONLY"))
                result = conn.execute(text(final_sql))
                rows = [dict(row._mapping) for row in result]
                if len(rows) > settings.mysql_max_rows:
                    log.warning(
                        "TG DB result capped at %d rows (original: %d+)",
                        settings.mysql_max_rows, settings.mysql_max_rows,
                    )
                    rows = rows[: settings.mysql_max_rows]
                return rows
        except PermissionError:
            raise
        except Exception as exc:
            log.error("TG DB query failed: %s", exc)
            return []

    def get_fixture_data(self) -> Dict[str, Any]:
        return _load_fixtures()


# Singleton
tg_db = TGDatabase()

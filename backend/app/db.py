from __future__ import annotations

import logging
from collections.abc import Iterator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

log = logging.getLogger("db")

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def _ensure_columns() -> None:
    """Lightweight additive migration: add any model columns missing from an
    existing table (e.g. after a schema change). create_all() only creates whole
    tables, it never alters existing ones — so new columns like `i18n_json` must
    be added here. Idempotent; safe on every startup. Only adds, never drops.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for table in SQLModel.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # create_all handled brand-new tables
        present = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in present:
                continue
            coltype = column.type.compile(dialect=engine.dialect)
            ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {coltype}'
            try:
                with engine.begin() as conn:
                    conn.execute(text(ddl))
                log.info("Migrated: added %s.%s (%s)", table.name, column.name, coltype)
            except Exception as exc:  # pragma: no cover - best effort
                log.warning("Could not add column %s.%s: %s", table.name, column.name, exc)


def init_db() -> None:
    # Import models so they are registered on SQLModel.metadata before create_all.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _ensure_columns()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session

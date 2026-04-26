from __future__ import annotations

from config.schema import SQLConfig


def postgresql_dsn(config: SQLConfig) -> str:
    if not config.dsn:
        raise ValueError("database.sql.dsn is required for PostgreSQL")
    return config.dsn

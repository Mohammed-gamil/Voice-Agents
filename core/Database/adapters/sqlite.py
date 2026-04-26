from __future__ import annotations

from config.schema import SQLConfig


def sqlite_dsn(config: SQLConfig) -> str:
    return config.dsn or "sqlite:///./agent_state.db"

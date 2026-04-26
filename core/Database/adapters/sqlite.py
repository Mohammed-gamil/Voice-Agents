from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config.schema import SQLConfig


def sqlite_dsn(config: SQLConfig) -> str:
    return config.dsn or "sqlite:///./data/agent_state.db"


class SQLiteAdapter:
    def __init__(self, config: SQLConfig) -> None:
        self.path = _sqlite_path(sqlite_dsn(config))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize)

    async def remember_conversation_fact(self, tenant_id: str, key: str, value: str) -> None:
        await asyncio.to_thread(self._remember_conversation_fact, tenant_id, key, value)

    async def create_ticket(self, tenant_id: str, payload: dict[str, Any]) -> str:
        return await asyncio.to_thread(self._create_ticket, tenant_id, payload)

    async def update_crm_record(self, tenant_id: str, account_name: str, field: str, value: str) -> None:
        await asyncio.to_thread(self._update_crm_record, tenant_id, account_name, field, value)

    async def queue_email(self, tenant_id: str, payload: dict[str, Any], status: str = "queued") -> str:
        return await asyncio.to_thread(self._queue_email, tenant_id, payload, status)

    async def semantic_search(self, tenant_id: str, query: str, limit: int = 5) -> list[dict[str, str]]:
        return await asyncio.to_thread(self._semantic_search, tenant_id, query, limit)

    async def close(self) -> None:
        return None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversation_facts (
                    tenant_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, key)
                );

                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    external_id TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS crm_records (
                    tenant_id TEXT NOT NULL,
                    account_name TEXT NOT NULL,
                    field TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, account_name, field)
                );

                CREATE TABLE IF NOT EXISTS email_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _remember_conversation_fact(self, tenant_id: str, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_facts (tenant_id, key, value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(tenant_id, key)
                DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (tenant_id, key, value, _now()),
            )

    def _create_ticket(self, tenant_id: str, payload: dict[str, Any]) -> str:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tickets (tenant_id, title, description, priority, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    payload["title"],
                    payload["description"],
                    payload["priority"],
                    json.dumps(payload),
                    _now(),
                ),
            )
            return f"{tenant_id.upper()}-{cursor.lastrowid:06d}"

    def _update_crm_record(self, tenant_id: str, account_name: str, field: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO crm_records (tenant_id, account_name, field, value, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, account_name, field)
                DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (tenant_id, account_name, field, value, _now()),
            )

    def _queue_email(self, tenant_id: str, payload: dict[str, Any], status: str = "queued") -> str:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO email_outbox (tenant_id, recipient, subject, summary, payload_json, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    payload["recipient"],
                    payload["subject"],
                    payload["summary"],
                    json.dumps(payload),
                    status,
                    _now(),
                ),
            )
            return f"EMAIL-{cursor.lastrowid:06d}"

    def _semantic_search(self, tenant_id: str, query: str, limit: int = 5) -> list[dict[str, str]]:
        like = f"%{query}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT key, value FROM conversation_facts
                WHERE tenant_id = ? AND (key LIKE ? OR value LIKE ?)
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (tenant_id, like, like, limit),
            ).fetchall()
            return [{"key": row["key"], "value": row["value"]} for row in rows]


def _sqlite_path(dsn: str) -> Path:
    if dsn.startswith("sqlite:///"):
        return Path(dsn.removeprefix("sqlite:///")).resolve()
    if dsn.startswith("sqlite://"):
        return Path(dsn.removeprefix("sqlite://")).resolve()
    return Path(dsn).resolve()


def _now() -> str:
    return datetime.now(UTC).isoformat()

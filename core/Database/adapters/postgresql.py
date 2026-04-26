from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from config.schema import SQLConfig


class PostgresAdapter:
    def __init__(self, config: SQLConfig) -> None:
        if not config.dsn:
            raise ValueError("database.sql.dsn is required for PostgreSQL")
        self.dsn = config.dsn
        self.schema = _safe_identifier(config.schema_name)
        self.pool: Any | None = None

    async def initialize(self) -> None:
        import asyncpg

        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.dsn)
        async with self.pool.acquire() as conn:
            await conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema}"')
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".conversation_facts (
                    tenant_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    PRIMARY KEY (tenant_id, key)
                )
                """
            )
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".tickets (
                    id BIGSERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    payload_json JSONB NOT NULL,
                    external_id TEXT,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".crm_records (
                    tenant_id TEXT NOT NULL,
                    account_name TEXT NOT NULL,
                    field TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    PRIMARY KEY (tenant_id, account_name, field)
                )
                """
            )
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".email_outbox (
                    id BIGSERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload_json JSONB NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )

    async def remember_conversation_fact(self, tenant_id: str, key: str, value: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO "{self.schema}".conversation_facts (tenant_id, key, value, updated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (tenant_id, key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
                """,
                tenant_id,
                key,
                value,
                _now(),
            )

    async def create_ticket(self, tenant_id: str, payload: dict[str, Any]) -> str:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                INSERT INTO "{self.schema}".tickets
                    (tenant_id, title, description, priority, payload_json, created_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                RETURNING id
                """,
                tenant_id,
                payload["title"],
                payload["description"],
                payload["priority"],
                json.dumps(payload),
                _now(),
            )
            return f"{tenant_id.upper()}-{row['id']:06d}"

    async def update_crm_record(self, tenant_id: str, account_name: str, field: str, value: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO "{self.schema}".crm_records (tenant_id, account_name, field, value, updated_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (tenant_id, account_name, field)
                DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
                """,
                tenant_id,
                account_name,
                field,
                value,
                _now(),
            )

    async def queue_email(self, tenant_id: str, payload: dict[str, Any], status: str = "queued") -> str:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                INSERT INTO "{self.schema}".email_outbox
                    (tenant_id, recipient, subject, summary, payload_json, status, created_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
                RETURNING id
                """,
                tenant_id,
                payload["recipient"],
                payload["subject"],
                payload["summary"],
                json.dumps(payload),
                status,
                _now(),
            )
            return f"EMAIL-{row['id']:06d}"

    async def semantic_search(self, tenant_id: str, query: str, limit: int = 5) -> list[dict[str, str]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT key, value FROM "{self.schema}".conversation_facts
                WHERE tenant_id = $1 AND (key ILIKE $2 OR value ILIKE $2)
                ORDER BY updated_at DESC
                LIMIT $3
                """,
                tenant_id,
                f"%{query}%",
                limit,
            )
            return [{"key": row["key"], "value": row["value"]} for row in rows]

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()


def _safe_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"unsafe PostgreSQL schema identifier: {value}")
    return value


def _now() -> datetime:
    return datetime.now(UTC)

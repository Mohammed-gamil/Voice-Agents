from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config.schema import DatabaseConfig
from core.Database.adapters.postgresql import PostgresAdapter
from core.Database.adapters.sqlite import SQLiteAdapter


@dataclass
class HybridDBClient:
    config: DatabaseConfig
    _adapter: Any = field(init=False, repr=False)
    _initialized: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.config.sql.adapter == "sqlite":
            self._adapter = SQLiteAdapter(self.config.sql)
        elif self.config.sql.adapter == "postgresql":
            self._adapter = PostgresAdapter(self.config.sql)
        else:
            raise ValueError(f"unsupported SQL adapter: {self.config.sql.adapter}")

    async def initialize(self) -> None:
        if self._initialized:
            return
        await self._adapter.initialize()
        self._initialized = True

    async def close(self) -> None:
        await self._adapter.close()

    async def remember_conversation_fact(self, tenant_id: str, key: str, value: str) -> None:
        await self.initialize()
        await self._adapter.remember_conversation_fact(tenant_id, key, value)

    async def create_ticket(self, tenant_id: str, payload: dict[str, Any]) -> str:
        await self.initialize()
        return await self._adapter.create_ticket(tenant_id, payload)

    async def update_crm_record(self, tenant_id: str, account_name: str, field: str, value: str) -> None:
        await self.initialize()
        await self._adapter.update_crm_record(tenant_id, account_name, field, value)

    async def queue_email(self, tenant_id: str, payload: dict[str, Any], status: str = "queued") -> str:
        await self.initialize()
        return await self._adapter.queue_email(tenant_id, payload, status)

    async def semantic_search(self, tenant_id: str, query: str, limit: int = 5) -> list[dict[str, str]]:
        await self.initialize()
        return await self._adapter.semantic_search(tenant_id, query, limit)

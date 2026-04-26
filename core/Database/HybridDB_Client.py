from __future__ import annotations

from dataclasses import dataclass

from config.schema import DatabaseConfig


@dataclass
class HybridDBClient:
    config: DatabaseConfig

    async def close(self) -> None:
        return None

    async def remember_conversation_fact(self, tenant_id: str, key: str, value: str) -> None:
        return None

    async def semantic_search(self, tenant_id: str, query: str, limit: int = 5) -> list[dict[str, str]]:
        return []

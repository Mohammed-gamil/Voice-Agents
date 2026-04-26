from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationData:
    tenant_id: str
    tool_messages: dict[str, str] = field(default_factory=dict)
    integrations: Any | None = None
    db: Any | None = None
    selected_intent: str | None = None
    facts: dict[str, str] = field(default_factory=dict)
    handoff_summary: str | None = None

    def remember(self, key: str, value: str) -> None:
        self.facts[key] = value

from __future__ import annotations

from dataclasses import dataclass

from config.schema import TenantConfig
from core.conversation import ConversationData


@dataclass(frozen=True)
class HumanHandoffPayload:
    tenant_id: str
    transfer_target: str | None
    summary: str
    selected_intent: str | None


def build_human_handoff_payload(config: TenantConfig, data: ConversationData) -> HumanHandoffPayload:
    summary = data.handoff_summary or "; ".join(f"{key}: {value}" for key, value in data.facts.items())
    return HumanHandoffPayload(
        tenant_id=config.tenant_id,
        transfer_target=config.telephony.warm_transfer_target,
        summary=summary or "No summary captured yet.",
        selected_intent=data.selected_intent,
    )

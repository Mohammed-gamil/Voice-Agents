from __future__ import annotations

from agents.handoff.human_handoff import HumanHandoffPayload


async def warm_transfer_to_human(payload: HumanHandoffPayload) -> str:
    if not payload.transfer_target:
        raise ValueError("warm transfer target is not configured")
    return f"Warm transfer prepared for {payload.transfer_target}."

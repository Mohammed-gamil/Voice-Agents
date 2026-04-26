from __future__ import annotations

import logging

from livekit.agents import RunContext, function_tool

from core.conversation import ConversationData
from tools.custom_actions.integrations import post_json
from tools.custom_actions.progress import speak_tool_progress


logger = logging.getLogger(__name__)


@function_tool()
async def create_ticket(
    context: RunContext[ConversationData],
    title: str,
    description: str,
    priority: str = "normal",
) -> str:
    """Create a support ticket for follow-up.

    Args:
        title: Short title for the issue.
        description: Full issue summary.
        priority: Ticket priority such as low, normal, high, or urgent.
    """

    await speak_tool_progress(context, "ticket_create")
    payload = {
        "tenant_id": context.userdata.tenant_id,
        "title": title,
        "description": description,
        "priority": priority,
    }
    ticket_id = await context.userdata.db.create_ticket(context.userdata.tenant_id, payload)
    payload["ticket_id"] = ticket_id
    integration_result = await post_json(context.userdata.integrations.ticketing, payload)

    logger.info("created ticket %s with priority %s", ticket_id, priority)
    if integration_result:
        external_id = integration_result.get("id") or integration_result.get("ticket_id") or integration_result.get("status")
        return f"Created ticket {ticket_id}. External service result: {external_id}."
    return f"Created ticket {ticket_id} and stored it in the tenant database."

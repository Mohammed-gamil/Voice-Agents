from __future__ import annotations

import logging

from livekit.agents import RunContext, function_tool

from core.conversation import ConversationData
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
    ticket_id = f"{context.userdata.tenant_id.upper()}-TICKET"
    logger.info("created ticket %s with priority %s", ticket_id, priority)
    return f"Created ticket {ticket_id}."

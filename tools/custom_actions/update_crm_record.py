from __future__ import annotations

import logging

from livekit.agents import RunContext, function_tool

from core.conversation import ConversationData
from tools.custom_actions.progress import speak_tool_progress


logger = logging.getLogger(__name__)


@function_tool()
async def update_crm_record(
    context: RunContext[ConversationData],
    account_name: str,
    field: str,
    value: str,
) -> str:
    """Update a CRM field after the user confirms the change.

    Args:
        account_name: Customer or account name.
        field: CRM field to update.
        value: New value for the field.
    """

    await speak_tool_progress(context, "crm_update")
    context.userdata.remember(f"crm.{account_name}.{field}", value)
    logger.info("updated CRM record for %s: %s=%s", account_name, field, value)
    return f"Updated {field} for {account_name}."

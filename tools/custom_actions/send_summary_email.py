from __future__ import annotations

import logging

from livekit.agents import RunContext, function_tool

from core.conversation import ConversationData
from tools.custom_actions.progress import speak_tool_progress


logger = logging.getLogger(__name__)


@function_tool()
async def send_summary_email(
    context: RunContext[ConversationData],
    recipient: str,
    subject: str,
    summary: str,
) -> str:
    """Send a conversation summary email after explicit user consent.

    Args:
        recipient: Email recipient.
        subject: Email subject.
        summary: Body text to send.
    """

    await speak_tool_progress(context, "email_send")
    context.userdata.handoff_summary = summary
    logger.info("queued summary email to %s", recipient)
    return f"Queued summary email to {recipient}."

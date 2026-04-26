from __future__ import annotations

from livekit.agents import RunContext

from core.conversation import ConversationData


async def speak_tool_progress(
    context: RunContext[ConversationData],
    message_key: str = "default",
) -> None:
    context.disallow_interruptions()
    phrase = (
        context.userdata.tool_messages.get(message_key)
        or context.userdata.tool_messages.get("default")
        or "Hmm, one moment please."
    )
    speech = context.session.generate_reply(
        instructions=f"Say exactly this short progress phrase, then stop: {phrase}",
        allow_interruptions=False,
    )
    await speech.wait_for_playout()

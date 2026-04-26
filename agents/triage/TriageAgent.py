from __future__ import annotations

from livekit.agents import RunContext, function_tool

from agents.base import TenantAgent
from agents.handoff.agent_handoff import build_specialist_agent, context_for_handoff, find_route
from config.schema import TenantConfig
from core.conversation import ConversationData


class TriageAgent(TenantAgent):
    def __init__(self, config: TenantConfig) -> None:
        super().__init__(
            config,
            config.agents.triage.prompt_key,
            include_custom_tools=False,
        )

    @function_tool()
    async def route_to_specialist(
        self,
        context: RunContext[ConversationData],
        intent: str,
    ):
        """Transfer the conversation to the specialist for the detected intent.

        Args:
            intent: One of the configured routing intents, such as sales, support, or billing.
        """

        route = find_route(self.config, intent)
        context.userdata.selected_intent = route.intent
        await self.session.generate_reply(
            instructions=f"Briefly tell the user you are transferring them to {route.intent}.",
            allow_interruptions=False,
        )
        return build_specialist_agent(
            self.config,
            route.agent_class,
            route.prompt_key,
            context_for_handoff(self),
        )

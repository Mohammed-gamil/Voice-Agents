from __future__ import annotations

from livekit.agents import ChatContext, RunContext, function_tool

from agents.base import TenantAgent
from config.schema import TenantConfig
from core.conversation import ConversationData


class SalesAgent(TenantAgent):
    def __init__(self, config: TenantConfig, prompt_key: str, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(config, prompt_key, chat_ctx=chat_ctx)

    @function_tool()
    async def qualify_lead(
        self,
        context: RunContext[ConversationData],
        company: str,
        use_case: str,
        timeline: str,
    ) -> str:
        """Record lead qualification details.

        Args:
            company: Prospect company name.
            use_case: What the prospect wants to solve.
            timeline: Expected buying or implementation timeline.
        """

        context.userdata.remember("lead.company", company)
        context.userdata.remember("lead.use_case", use_case)
        context.userdata.remember("lead.timeline", timeline)
        return "Lead details recorded."

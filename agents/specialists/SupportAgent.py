from __future__ import annotations

from livekit.agents import ChatContext, RunContext, function_tool

from agents.base import TenantAgent
from config.schema import TenantConfig
from core.conversation import ConversationData


class SupportAgent(TenantAgent):
    def __init__(self, config: TenantConfig, prompt_key: str, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(config, prompt_key, chat_ctx=chat_ctx)

    @function_tool()
    async def record_issue(
        self,
        context: RunContext[ConversationData],
        product_area: str,
        symptoms: str,
        severity: str = "normal",
    ) -> str:
        """Record a support issue before troubleshooting or ticket creation.

        Args:
            product_area: Affected product area.
            symptoms: User-visible symptoms.
            severity: Current severity estimate.
        """

        context.userdata.remember("support.product_area", product_area)
        context.userdata.remember("support.symptoms", symptoms)
        context.userdata.remember("support.severity", severity)
        return "Issue details recorded."

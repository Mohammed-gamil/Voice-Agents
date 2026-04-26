from __future__ import annotations

from livekit.agents import ChatContext, RunContext, function_tool

from agents.base import TenantAgent
from config.schema import TenantConfig
from core.conversation import ConversationData


class BillingAgent(TenantAgent):
    def __init__(self, config: TenantConfig, prompt_key: str, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(config, prompt_key, chat_ctx=chat_ctx)

    @function_tool()
    async def record_billing_case(
        self,
        context: RunContext[ConversationData],
        account_name: str,
        billing_topic: str,
    ) -> str:
        """Record a billing case for invoices, subscriptions, or payments.

        Args:
            account_name: Customer account name.
            billing_topic: Billing issue or request.
        """

        context.userdata.remember("billing.account_name", account_name)
        context.userdata.remember("billing.topic", billing_topic)
        return "Billing case details recorded."

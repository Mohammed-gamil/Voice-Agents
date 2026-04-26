from __future__ import annotations

from livekit.agents import Agent, ChatContext

from agents.specialists.BillingAgent import BillingAgent
from agents.specialists.SalesAgent import SalesAgent
from agents.specialists.SupportAgent import SupportAgent
from config.schema import RoutingRule, TenantConfig


_AGENT_REGISTRY = {
    "SalesAgent": SalesAgent,
    "SupportAgent": SupportAgent,
    "BillingAgent": BillingAgent,
}


def find_route(config: TenantConfig, intent: str) -> RoutingRule:
    normalized = intent.strip().lower()
    for rule in config.agents.routing.rules:
        if rule.intent.lower() == normalized:
            return rule
    valid = ", ".join(rule.intent for rule in config.agents.routing.rules)
    raise ValueError(f"unknown intent '{intent}'. Valid intents: {valid}")


def build_specialist_agent(
    config: TenantConfig,
    agent_class: str,
    prompt_key: str,
    chat_ctx: ChatContext | None,
) -> Agent:
    try:
        cls = _AGENT_REGISTRY[agent_class]
    except KeyError as exc:
        known = ", ".join(sorted(_AGENT_REGISTRY))
        raise ValueError(f"unknown agent class '{agent_class}'. Known agents: {known}") from exc
    return cls(config, prompt_key, chat_ctx=chat_ctx)


def context_for_handoff(source: Agent) -> ChatContext | None:
    if not source.chat_ctx:
        return None
    return source.chat_ctx.copy(exclude_instructions=True)

from __future__ import annotations

from typing import Any

from livekit.agents import AgentSession, mcp

from config.schema import TenantConfig
from core.Pipeline.PipelineFactory import build_pipeline
from core.conversation import ConversationData


def build_agent_session(config: TenantConfig, *, prewarmed_vad: Any | None = None) -> AgentSession[ConversationData]:
    pipeline = build_pipeline(config.pipeline, config.vad, prewarmed_vad=prewarmed_vad)
    kwargs: dict[str, Any] = {
        "llm": pipeline.llm,
        "userdata": ConversationData(
            tenant_id=config.tenant_id,
            tool_messages=config.conversation.tool_messages,
        ),
        "turn_handling": _turn_handling(config),
        "mcp_servers": _mcp_servers(config),
    }

    if pipeline.vad is not None:
        kwargs["vad"] = pipeline.vad
    if pipeline.stt is not None:
        kwargs["stt"] = pipeline.stt
    if pipeline.tts is not None:
        kwargs["tts"] = pipeline.tts

    return AgentSession[ConversationData](**kwargs)


def _turn_handling(config: TenantConfig) -> dict[str, Any]:
    turn = config.turn
    turn_handling: dict[str, Any] = {
        "interruption": {
            "enabled": turn.allow_interruptions,
            "mode": turn.interruption_mode,
            "min_duration": turn.min_interruption_duration,
            "min_words": turn.min_interruption_words,
            "false_interruption_timeout": turn.false_interruption_timeout,
            "resume_false_interruption": turn.resume_false_interruption,
        },
        "endpointing": {
            "min_delay": turn.min_endpointing_delay,
            "max_delay": turn.max_endpointing_delay,
        },
        "preemptive_generation": {
            "enabled": turn.preemptive_generation,
        },
    }
    if turn.turn_detection:
        turn_handling["turn_detection"] = turn.turn_detection
    return turn_handling


def _mcp_servers(config: TenantConfig) -> list[mcp.MCPServer]:
    servers: list[mcp.MCPServer] = []
    for server in config.tools.mcp_servers:
        if not server.enabled:
            continue
        servers.append(
            mcp.MCPServerHTTP(
                server.url,
                allowed_tools=server.allowed_tools,
                headers=server.headers,
            )
        )
    return servers

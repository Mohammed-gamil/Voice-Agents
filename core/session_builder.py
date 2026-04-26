from __future__ import annotations

from typing import Any

from livekit.agents import mcp

from config.schema import TenantConfig
from core.Database.HybridDB_Client import HybridDBClient
from core.Pipeline.PipelineFactory import build_pipeline
from core.conversation import ConversationData
from agents.base import TenantAgent


def build_agent_session(config: TenantConfig, *, prewarmed_vad: Any | None = None) -> TenantAgent:
    pipeline = build_pipeline(config.pipeline, config.vad, prewarmed_vad=prewarmed_vad)
    
    # We set up ConversationData and potentially pass it if we were doing custom context.
    # But VoicePipelineAgent just needs the components.
    
    return TenantAgent(
        config=config,
        prompt_key="default",
        vad=pipeline.vad,
        stt=pipeline.stt,
        llm_plugin=pipeline.llm,
        tts=pipeline.tts,
        turn_handling=_turn_handling(config) if config.turn else None,
    )


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

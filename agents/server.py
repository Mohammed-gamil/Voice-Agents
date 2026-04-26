from __future__ import annotations

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from livekit.agents import AgentServer, JobContext, cli
from livekit.agents import RoomInputOptions, RoomOutputOptions

from agents.triage.TriageAgent import TriageAgent
from config.schema import TenantConfig
from core.Observability.otel_tracing import configure_tracing
from core.Observability.telemetry import attach_session_observability
from core.Pipeline.vad_prewarm import prewarm
from core.config_loader import load_tenant_config
from core.session_builder import build_agent_session


logger = logging.getLogger("tenant-agent-server")

load_dotenv(dotenv_path=".env.local")

server = AgentServer(load_threshold=0.9)
server.setup_fnc = prewarm


def compute_load(agent_server: AgentServer) -> float:
    return min(len(agent_server.active_jobs) / 10, 1.0)


server.load_fnc = compute_load


@server.rtc_session(agent_name=os.getenv("LIVEKIT_AGENT_NAME", "tenant-voice-agent"))
async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()
    config = load_tenant_config(_tenant_id_from_room(ctx))
    configure_tracing(config)

    prewarmed_vad = ctx.proc.userdata.get("vad") if config.vad.prewarm else None
    session = build_agent_session(config, prewarmed_vad=prewarmed_vad)
    attach_session_observability(session, ctx, config)

    logger.info("starting tenant session", extra={"tenant": config.tenant_id, "room": ctx.room.name})
    await session.start(
        agent=_initial_agent(config),
        room=ctx.room,
        room_input_options=RoomInputOptions(),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )


def _initial_agent(config: TenantConfig):
    if config.agents.triage.class_name != "TriageAgent":
        raise ValueError("the current entrypoint expects agents.triage.class to be TriageAgent")
    return TriageAgent(config)


def _tenant_id_from_room(ctx: JobContext) -> str | None:
    metadata = getattr(ctx.room, "metadata", None)
    if not metadata:
        return os.getenv("TENANT_ID")
    try:
        parsed: dict[str, Any] = json.loads(metadata)
    except json.JSONDecodeError:
        logger.warning("room metadata is not JSON; falling back to TENANT_ID")
        return os.getenv("TENANT_ID")
    return parsed.get("tenant_id") or parsed.get("tenant")


def main() -> None:
    cli.run_app(server)


if __name__ == "__main__":
    main()

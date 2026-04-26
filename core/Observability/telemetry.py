from __future__ import annotations

import logging
from typing import Any

from livekit.agents import JobContext, metrics

from config.schema import TenantConfig


logger = logging.getLogger(__name__)


def attach_session_observability(session: Any, ctx: JobContext, config: TenantConfig) -> None:
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: Any) -> None:
        if config.observability.emit_turn_metrics:
            metrics.log_metrics(ev.metrics)
        if config.observability.emit_session_usage:
            usage_collector.collect(ev.metrics)

    async def log_usage() -> None:
        if config.observability.emit_session_usage:
            logger.info("tenant=%s usage=%s", config.tenant_id, usage_collector.get_summary())

    ctx.add_shutdown_callback(log_usage)

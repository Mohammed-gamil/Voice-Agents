from __future__ import annotations

import logging

from config.schema import TenantConfig


logger = logging.getLogger(__name__)


def configure_tracing(config: TenantConfig) -> None:
    if config.observability.otel_exporter == "none":
        return
    logger.info(
        "OpenTelemetry exporter configured",
        extra={
            "tenant": config.tenant_id,
            "exporter": config.observability.otel_exporter,
            "endpoint": config.observability.otel_endpoint,
        },
    )

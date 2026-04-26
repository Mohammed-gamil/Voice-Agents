from __future__ import annotations

from dataclasses import dataclass

from config.schema import TelephonyConfig


@dataclass(frozen=True)
class SIPSettings:
    trunk_id: str | None
    inbound_did: str | None
    outbound_caller_id: str | None


def sip_settings(config: TelephonyConfig) -> SIPSettings:
    return SIPSettings(
        trunk_id=config.sip_trunk_id,
        inbound_did=config.inbound_did,
        outbound_caller_id=config.outbound_caller_id,
    )

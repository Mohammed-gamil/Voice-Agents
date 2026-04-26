from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tools.custom_actions.create_ticket import create_ticket
from tools.custom_actions.send_summary_email import send_summary_email
from tools.custom_actions.update_crm_record import update_crm_record


_REGISTRY: dict[str, Callable[..., Any]] = {
    "create_ticket": create_ticket,
    "update_crm_record": update_crm_record,
    "send_summary_email": send_summary_email,
}


def load_custom_tools(names: list[str]) -> list[Callable[..., Any]]:
    missing = sorted(set(names) - set(_REGISTRY))
    if missing:
        raise KeyError(f"unknown custom action(s): {', '.join(missing)}")
    return [_REGISTRY[name] for name in names]

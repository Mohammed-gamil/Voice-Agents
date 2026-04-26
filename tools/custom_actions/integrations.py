from __future__ import annotations

import asyncio
import json
import os
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage
from typing import Any

from config.schema import EmailServiceConfig, HTTPServiceConfig


async def post_json(config: HTTPServiceConfig, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not config.enabled:
        return None
    if not config.url or config.url.startswith("${"):
        raise ValueError("enabled HTTP integration requires a concrete url")

    return await asyncio.to_thread(_post_json_sync, config, payload)


async def send_email(config: EmailServiceConfig, recipient: str, subject: str, body: str) -> str | None:
    if not config.enabled:
        return None
    if not config.smtp_host or config.smtp_host.startswith("${"):
        raise ValueError("enabled SMTP integration requires smtp_host")
    if not config.from_email or config.from_email.startswith("${"):
        raise ValueError("enabled SMTP integration requires from_email")

    return await asyncio.to_thread(_send_email_sync, config, recipient, subject, body)


def _post_json_sync(config: HTTPServiceConfig, payload: dict[str, Any]) -> dict[str, Any]:
    headers = {"Content-Type": "application/json", **config.headers}
    if config.auth_token_env:
        token = os.getenv(config.auth_token_env)
        if not token:
            raise ValueError(f"{config.auth_token_env} is required for enabled HTTP integration")
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        config.url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method=config.method,
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            body = response.read().decode("utf-8")
            if not body:
                return {"status": response.status}
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"body": body}
            parsed.setdefault("status", response.status)
            return parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP integration failed with {exc.code}: {body}") from exc


def _send_email_sync(config: EmailServiceConfig, recipient: str, subject: str, body: str) -> str:
    username = os.getenv(config.username_env or "") if config.username_env else None
    password = os.getenv(config.password_env or "") if config.password_env else None

    message = EmailMessage()
    message["From"] = config.from_email
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=15) as smtp:
        if config.use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)
    return f"SMTP:{recipient}"

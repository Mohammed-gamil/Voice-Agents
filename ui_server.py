from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from livekit import api


ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class UITestHandler(BaseHTTPRequestHandler):
    server_version = "LiveKitAgentTestUI/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/config":
            self._send_json(
                {
                    "livekitUrl": os.getenv("LIVEKIT_URL", ""),
                    "tenantId": os.getenv("TENANT_ID", "acme_corp"),
                    "agentName": os.getenv("LIVEKIT_AGENT_NAME", "tenant-voice-agent"),
                }
            )
            return

        path = "/index.html" if parsed.path in {"", "/"} else parsed.path
        safe_path = Path(path.lstrip("/"))
        file_path = (WEB_DIR / safe_path).resolve()
        if not str(file_path).startswith(str(WEB_DIR.resolve())) or not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/token":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self._read_json()
            token_payload = create_token(payload)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._send_json(token_payload)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[ui] {self.address_string()} - {fmt % args}")

    def _read_json(self) -> dict[str, str]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}
        raw = self.rfile.read(content_length)
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def create_token(payload: dict[str, str]) -> dict[str, str]:
    livekit_url = payload.get("livekitUrl") or os.getenv("LIVEKIT_URL", "")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    if not livekit_url:
        raise ValueError("LIVEKIT_URL is required")
    if not api_key or not api_secret:
        raise ValueError("LIVEKIT_API_KEY and LIVEKIT_API_SECRET are required")

    room = _clean(payload.get("room")) or f"agent-test-{os.getpid()}"
    identity = _clean(payload.get("identity")) or "tester"
    tenant_id = _clean(payload.get("tenantId")) or os.getenv("TENANT_ID", "acme_corp")
    agent_name = _clean(payload.get("agentName")) or os.getenv("LIVEKIT_AGENT_NAME", "tenant-voice-agent")

    room_config = api.RoomConfiguration(
        metadata=json.dumps({"tenant_id": tenant_id}),
        agents=[api.RoomAgentDispatch(agent_name=agent_name, metadata=json.dumps({"tenant_id": tenant_id}))],
    )
    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_metadata(json.dumps({"tenant_id": tenant_id, "role": "tester"}))
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .with_room_config(room_config)
        .to_jwt()
    )
    return {
        "token": token,
        "url": livekit_url,
        "room": room,
        "identity": identity,
        "tenantId": tenant_id,
        "agentName": agent_name,
    }


def _clean(value: str | None) -> str:
    return (value or "").strip()


def main() -> None:
    load_dotenv(ROOT / ".env.local")
    host = os.getenv("UI_HOST", DEFAULT_HOST)
    port = int(os.getenv("UI_PORT", str(DEFAULT_PORT)))
    qs = parse_qs(os.getenv("QUERY_STRING", ""))
    if "port" in qs:
        port = int(qs["port"][0])

    httpd = ThreadingHTTPServer((host, port), UITestHandler)
    print(f"LiveKit agent test UI: http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()

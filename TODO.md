# TODO

This list tracks the next practical steps for turning the current LiveKit voice-agent scaffold into a production-ready tenant platform.

## High Priority

- Replace placeholder custom actions with real service integrations:
  - `create_ticket`
  - `update_crm_record`
  - `send_summary_email`
- Implement durable database adapters in `core/Database/adapters/`.
- Add real tenant-specific eval suites under `observability/evals/`.
- Add authentication or local-network restrictions before exposing `ui_server.py` outside local development.
- Confirm production model/provider choices for each tenant in `config/tenant_config.yaml`.

## Agent Behavior

- Expand scenario definitions under `conversation.scenarios`.
- Add tenant-specific greetings for every specialist agent.
- Add more progress phrase keys for long-running tools, billing actions, and human handoff.
- Add confirmation flows before irreversible tool calls.
- Add structured memory fields for account name, caller identity, intent, and consent.

## Voice And UX

- Add optional frontend earcons for waiting, success, and error states.
- Improve transcript rendering for partial and final LiveKit transcription segments.
- Add visible room, participant, and agent connection diagnostics to the test UI.
- Add a push-to-talk mode for noisy environments.

## Telephony

- Implement warm transfer behavior in `core/Telephony/Transfers.py`.
- Connect SIP trunk settings from tenant config to LiveKit SIP APIs.
- Add DTMF intent routing using `telephony.dtmf_map`.
- Add operator handoff summaries for human support queues.

## Observability

- Connect OpenTelemetry exporter setup in `core/Observability/otel_tracing.py`.
- Add dashboard templates in `observability/dashboards/`.
- Track per-tenant latency, interruption, STT confidence, and tool-call metrics.
- Add alerting for failed tool calls and failed agent dispatches.

## Deployment

- Add Dockerfile and production start command.
- Add `.env.production.example`.
- Add CI checks for compile, config validation, and linting.
- Document LiveKit Cloud deployment steps.

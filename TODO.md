# TODO

This list tracks the next practical steps for turning the current LiveKit voice-agent scaffold into a production-ready tenant platform.

## High Priority

- Wire production credentials in `.env.local` or deployment secrets:
  - `DATABASE_DSN`
  - `TICKETING_WEBHOOK_URL`
  - `TICKETING_API_TOKEN`
  - `CRM_WEBHOOK_URL`
  - `CRM_API_TOKEN`
  - `SMTP_HOST`
  - `SMTP_USERNAME`
  - `SMTP_PASSWORD`
  - `SMTP_FROM_EMAIL`
- Decide whether to enable outbound ticketing, CRM, and SMTP integrations per tenant.
- Add a CI job that runs config validation and compile checks.
- Add a real eval runner that executes `observability/evals/acme_evals.yaml`.

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

## Completed

- Replaced placeholder custom actions with durable database writes and optional HTTP/SMTP integrations.
- Implemented SQLite and PostgreSQL database adapters.
- Switched the default Acme tenant to PostgreSQL.
- Added tenant-specific eval fixtures under `observability/evals/acme_evals.yaml`.
- Added local UI authentication and remote-exposure guardrails.
- Confirmed production model/provider choices in `config/tenant_config.yaml`.

# Technical Guide

This project is a configurable, multi-tenant LiveKit voice agent runtime. It uses a LiveKit `AgentServer` to accept jobs, an `AgentSession` to run the voice pipeline, YAML tenant configuration to choose models and routing behavior, and a small browser UI for local testing.

## 1. What You Run

There are two local processes during development:

```console
python main.py dev
python ui_server.py
```

`python main.py dev` starts the LiveKit agent worker. The worker registers with LiveKit and waits for rooms that dispatch `LIVEKIT_AGENT_NAME`.

`python ui_server.py` starts the local browser tester at:

```text
http://127.0.0.1:8765
```

The UI creates a participant token, joins a LiveKit room, publishes your microphone, receives agent audio, and displays transcript events when LiveKit sends them.

## 2. Install And Configure

Create and activate a virtual environment:

```console
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Copy the example environment file:

```console
copy .env.example .env.local
```

Required values:

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
LIVEKIT_AGENT_NAME=tenant-voice-agent
TENANT_ID=acme_corp
```

Provider keys and database settings depend on the tenant config:

```env
OPENAI_API_KEY=required_for_openai_direct_or_realtime
DEEPGRAM_API_KEY=required_for_deepgram_direct
CARTESIA_API_KEY=required_for_cartesia_direct
DATABASE_DSN=postgresql://voice_agent:change_me@localhost:5432/voice_agents
```

The default tenant uses LiveKit Inference descriptors for the cascaded pipeline, so LiveKit credentials are the main required keys. If you switch to direct provider plugins or S2S realtime mode, add the matching provider key.

## 3. Runtime Flow

The high-level request path is:

```text
Browser UI
  -> ui_server.py creates LiveKit token
  -> browser joins LiveKit room
  -> LiveKit dispatches configured agent
  -> agents/server.py receives JobContext
  -> core/config_loader.py loads tenant config
  -> core/session_builder.py builds AgentSession
  -> agents/triage/TriageAgent.py starts conversation
  -> specialist agent handles routed intent
```

Important files:

```text
main.py                              thin entrypoint into agents.server
agents/server.py                     LiveKit AgentServer and job entrypoint
ui_server.py                         local browser test server and token endpoint
web/index.html                       test UI markup
web/app.js                           LiveKit browser client logic
config/tenant_config.yaml            tenant source of truth
config/defaults.yaml                 fallback config values
config/schema.py                     Pydantic validation schema
core/config_loader.py                YAML loading and default merging
core/session_builder.py              AgentSession constructor surface
core/Pipeline/PipelineFactory.py     STT, LLM, TTS, VAD, realtime construction
agents/triage/TriageAgent.py         intent detection and routing
agents/specialists/*.py              Sales, support, billing agents
tools/custom_actions/*.py            custom function tools
```

## 4. Tenant Configuration

Tenants live in `config/tenant_config.yaml`.

Minimal shape:

```yaml
tenants:
  acme_corp:
    display_name: Acme Corp Assistant
    pipeline:
      mode: hybrid
      stt:
        provider: livekit_inference
        model: deepgram/nova-3
        language: multi
      llm:
        provider: livekit_inference
        model: openai/gpt-5-mini
      tts:
        provider: livekit_inference
        model: cartesia/sonic-3
        voice_id: 9626c31c-bec5-4cca-baa8-f8ba9e84c8bc
    agents:
      triage:
        class: TriageAgent
        prompt_key: triage_system
      routing:
        rules:
          - intent: sales
            agent_class: SalesAgent
            prompt_key: sales_system
    prompts:
      triage_system: |
        Route the user to the correct specialist.
      sales_system: |
        You are the sales assistant.
```

The config is validated at startup by `config/schema.py`. Unknown fields fail fast because the schema forbids extras.

## 5. Pipeline Modes

`pipeline.mode` controls how the session is built:

```yaml
pipeline:
  mode: cascaded
```

Supported modes:

```text
cascaded    VAD -> STT -> LLM -> TTS
s2s         realtime speech-to-speech model
hybrid      cascaded by default, with config space reserved for realtime fast paths
```

The current implementation keeps hybrid realtime lazy. That means a hybrid tenant can run the normal cascaded path without requiring `OPENAI_API_KEY` unless you actually enable realtime usage.

Provider options currently represented in the schema:

```text
STT: deepgram, assemblyai, livekit_inference
LLM: openai, anthropic, livekit_inference
TTS: openai, cartesia, elevenlabs, livekit_inference
S2S: openai_realtime, google_realtime, xai_realtime
```

LiveKit Inference values are passed as model strings. Direct provider values instantiate the matching LiveKit plugin classes.

## 6. Running The Agent

Start the worker:

```console
python main.py dev
```

The worker:

1. Loads `.env.local`.
2. Registers an `AgentServer`.
3. Prewarms Silero VAD.
4. Waits for LiveKit jobs.
5. Reads tenant ID from room metadata.
6. Falls back to `TENANT_ID` when metadata is missing.

The room metadata format is:

```json
{"tenant_id": "acme_corp"}
```

The browser test UI sets this metadata for you through the generated token room configuration.

## 7. Testing With The Local UI

Start the UI:

```console
python ui_server.py
```

Open:

```text
http://127.0.0.1:8765
```

Then:

1. Confirm the LiveKit URL is filled in.
2. Confirm `Tenant` is `acme_corp`.
3. Confirm `Agent name` matches `LIVEKIT_AGENT_NAME`.
4. Click `Connect`.
5. Allow microphone access.
6. Speak to the agent.

The UI also has a text box. Text messages are sent on the LiveKit `lk.chat` topic. `AgentSession` treats this as text input, which is useful when microphone permissions or audio devices are unreliable.

## 8. Adding A New Tenant

Add a new block in `config/tenant_config.yaml`:

```yaml
tenants:
  new_client:
    display_name: New Client Assistant
    agents:
      triage:
        class: TriageAgent
        prompt_key: triage_system
      routing:
        rules:
          - intent: support
            agent_class: SupportAgent
            prompt_key: support_system
    prompts:
      triage_system: |
        Identify the user's intent and route them.
      support_system: |
        Help the user solve support issues.
```

Any missing pipeline, turn, VAD, tools, telephony, database, or observability fields are merged from `config/defaults.yaml`.

To test the new tenant, either set:

```env
TENANT_ID=new_client
```

or enter `new_client` in the UI Tenant field before connecting.

## 9. Adding A Specialist Agent

Create a new agent file under `agents/specialists/`, for example:

```python
from __future__ import annotations

from livekit.agents import ChatContext

from agents.base import TenantAgent
from config.schema import TenantConfig


class SchedulingAgent(TenantAgent):
    def __init__(self, config: TenantConfig, prompt_key: str, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(config, prompt_key, chat_ctx=chat_ctx)
```

Register it in `agents/handoff/agent_handoff.py`:

```python
from agents.specialists.SchedulingAgent import SchedulingAgent

_AGENT_REGISTRY = {
    "SchedulingAgent": SchedulingAgent,
}
```

Add a routing rule:

```yaml
agents:
  routing:
    rules:
      - intent: scheduling
        agent_class: SchedulingAgent
        prompt_key: scheduling_system
```

Add the matching prompt under `prompts`.

## 10. Adding Custom Tools

Tools live in `tools/custom_actions/`.

Create a tool:

```python
from livekit.agents import RunContext, function_tool

from core.conversation import ConversationData


@function_tool()
async def look_up_order(context: RunContext[ConversationData], order_id: str) -> str:
    """Look up an order by ID.

    Args:
        order_id: Customer order ID.
    """

    return f"Order {order_id} is processing."
```

Register it in `tools/custom_actions/registry.py`:

```python
from tools.custom_actions.look_up_order import look_up_order

_REGISTRY = {
    "look_up_order": look_up_order,
}
```

Enable it per tenant:

```yaml
tools:
  custom_actions:
    - look_up_order
```

For irreversible actions, call:

```python
context.disallow_interruptions()
```

This prevents user speech from cancelling the operation midway.

### Production Integrations

The built-in starter tools now do real work in two layers:

1. Persist the action through the configured database adapter.
2. Optionally call an external service if the tenant integration is enabled.

Tenant integration config:

```yaml
tools:
  integrations:
    ticketing:
      enabled: true
      url: ${TICKETING_WEBHOOK_URL}
      auth_token_env: TICKETING_API_TOKEN
    crm:
      enabled: true
      url: ${CRM_WEBHOOK_URL}
      auth_token_env: CRM_API_TOKEN
    email:
      enabled: true
      smtp_host: ${SMTP_HOST}
      username_env: SMTP_USERNAME
      password_env: SMTP_PASSWORD
      from_email: ${SMTP_FROM_EMAIL}
```

When `enabled: false`, the tool still writes to the tenant database. This is useful for local development and offline tests. When enabled, ticketing and CRM calls send JSON over HTTP with an optional bearer token. Email uses SMTP.

## 11. Greetings, Scenarios, And Tool Progress Phrases

Conversation behavior that changes per tenant should usually live in YAML, not Python.

### Greetings

Add greetings under `conversation.greetings`:

```yaml
conversation:
  greetings:
    TriageAgent: "Hi, this is Acme Corp. How can I help you today?"
    SalesAgent: "I can help with sales questions. What are you hoping to build?"
    SupportAgent: "I can help troubleshoot that. Tell me what is happening."
    BillingAgent: "I can help with billing. What account or invoice should we look at?"
```

`agents/base.py` checks this map in `on_enter()`. If a greeting exists for the current agent class, the agent says that greeting when it enters the session. If there is no configured greeting, the agent generates a normal opening from its prompt.

### Scenarios

Use scenarios for reusable behavior rules:

```yaml
conversation:
  scenarios:
    first_time_caller:
      description: Caller has not used Acme before.
      instructions: |
        Ask one short qualifying question before routing. Keep the greeting warm
        and avoid assuming the caller already has an account.
    returning_customer:
      description: Caller already has an Acme account.
      instructions: |
        Ask for the account name early and confirm the goal before using tools.
```

`agents/base.py` appends these scenario rules to every tenant agent's instructions. This gives the LLM a shared scenario playbook without hardcoding scenario logic in each agent class.

Use scenario config for conversation policy. Use Python tools only when the scenario requires an actual action, such as a database lookup or CRM update.

### Tool Progress Phrases

For writes, database updates, CRM updates, email sends, ticket creation, and other operations that may take a moment, configure phrases here:

```yaml
conversation:
  tool_messages:
    default: "Hmm, one moment please."
    database_write: "Hmm, please wait while I add your data."
    ticket_create: "Hmm, please wait while I create that ticket."
    crm_update: "Hmm, please wait while I update the customer record."
    email_send: "Hmm, please wait while I prepare that summary."
```

Tools call `speak_tool_progress()` before doing the action:

```python
from tools.custom_actions.progress import speak_tool_progress


@function_tool()
async def save_profile(context: RunContext[ConversationData], name: str) -> str:
    await speak_tool_progress(context, "database_write")
    await database.save_profile(name)
    return "Saved the profile."
```

The helper:

1. Calls `context.disallow_interruptions()`.
2. Generates a short progress phrase.
3. Waits for the phrase to finish playing.
4. Returns control to the tool so the database or external action can run.

This is the right place for spoken fillers like "Hmm" or "one moment." For real audio earcons, add a frontend sound or a LiveKit audio source later; spoken TTS phrases are simpler and work across WebRTC and SIP.

## 12. MCP Servers

MCP servers are declared per tenant:

```yaml
tools:
  mcp_servers:
    - name: crm
      url: https://crm.example.com/mcp
      enabled: true
      allowed_tools:
        - search_account
        - update_account
```

`core/session_builder.py` turns enabled entries into `MCPServerHTTP` objects and passes them to `AgentSession`.

## 13. Observability

Session metrics are attached in `core/Observability/telemetry.py`.

The current behavior:

```text
metrics_collected event -> metrics.log_metrics
metrics_collected event -> UsageCollector
shutdown callback       -> usage summary log
```

Tenant observability config:

```yaml
observability:
  log_level: INFO
  otel_exporter: none
  otel_endpoint:
  emit_session_usage: true
  emit_turn_metrics: true
  eval_suite: acme_evals.yaml
```

`core/Observability/otel_tracing.py` is a placeholder for connecting Datadog, Jaeger, or OTLP exporters.

## 14. Telephony And Database Layers

The repo includes scaffolded abstraction points:

```text
core/Telephony/SIP_Trunking.py
core/Telephony/Transfers.py
core/Database/HybridDB_Client.py
core/Database/adapters/
```

The default tenant is configured for PostgreSQL:

```yaml
database:
  sql:
    adapter: postgresql
    schema: acme_corp
    dsn: ${DATABASE_DSN}
```

`core/Database/adapters/postgresql.py` creates the tenant schema and durable tables on startup. The SQLite adapter remains available for quick local experiments, but production tenants should use PostgreSQL.

Expected PostgreSQL setup:

```sql
CREATE DATABASE voice_agents;
CREATE USER voice_agent WITH PASSWORD 'change_me';
GRANT ALL PRIVILEGES ON DATABASE voice_agents TO voice_agent;
```

Then set:

```env
DATABASE_DSN=postgresql://voice_agent:change_me@localhost:5432/voice_agents
```

The adapter creates the tenant schema from `database.sql.schema` and manages these tables:

```text
conversation_facts
tickets
crm_records
email_outbox
```

## 15. Eval Suites

Tenant eval suites live under `observability/evals/`.

The Acme suite is:

```text
observability/evals/acme_evals.yaml
```

It defines fixtures for sales routing, support ticket creation, billing routing, CRM updates, and summary email behavior. A future CI runner should execute these fixtures against a test LiveKit room or a model-level harness.

## 16. Common Commands

Validate Python syntax:

```console
python -m compileall agents config core tools main.py ui_server.py
```

Validate tenant loading:

```console
python -c "from core.config_loader import load_tenant_config; print(load_tenant_config('acme_corp').display_name)"
```

Start the worker:

```console
python main.py dev
```

Start the UI:

```console
python ui_server.py
```

Use another UI port:

```console
set UI_PORT=8770
python ui_server.py
```

## 17. Troubleshooting

`LIVEKIT_API_KEY and LIVEKIT_API_SECRET are required`

Check `.env.local`. The UI token endpoint cannot generate a room token without both values.

`database.sql.dsn is required for PostgreSQL`

Set `DATABASE_DSN` in `.env.local` or deployment secrets.

`enabled HTTP integration requires a concrete url`

An integration was enabled but its webhook URL env var is missing.

`unauthorized` from the UI API

If `UI_AUTH_TOKEN` is set, open the UI with `?token=your-token` or send `X-UI-Token`.

`The api_key client option must be set`

You are using a direct provider plugin or realtime model that needs a provider key, such as `OPENAI_API_KEY`.

Agent does not join the room

Confirm the worker is running with `python main.py dev`, confirm `LIVEKIT_AGENT_NAME` matches the UI Agent name field, and confirm room metadata contains the expected tenant.

Browser connects but no audio

Allow microphone permissions, check the browser's selected input device, and use the text input fallback to confirm the session is alive.

No transcript appears

Audio can still work even if transcript events are not shown. Confirm `RoomOutputOptions(transcription_enabled=True)` is still enabled in `agents/server.py`.

Config validation fails

The Pydantic schema forbids unknown keys. Compare the tenant YAML with `config/schema.py` and `config/defaults.yaml`.

## 18. Production Notes

For production:

1. Run `python main.py start` instead of dev mode.
2. Use a process manager or container runtime.
3. Keep `.env.local` out of source control.
4. Use real secrets with adequate entropy.
5. Implement durable database adapters.
6. Connect OpenTelemetry exporters if required.
7. Replace placeholder custom tools with real service integrations.
8. Add tenant eval suites under `observability/evals/`.

<a href="https://livekit.io/">
  <img src="./.github/assets/livekit-mark.png" alt="LiveKit logo" width="100" height="100">
</a>

# LiveKit Tenant Voice Agents

<p>
  <a href="https://cloud.livekit.io/projects/p_/sandbox"><strong>Deploy a sandbox app</strong></a>
  •
  <a href="https://docs.livekit.io/agents/overview/">LiveKit Agents Docs</a>
  •
  <a href="https://livekit.io/cloud">LiveKit Cloud</a>
  •
  <a href="https://blog.livekit.io/">Blog</a>
</p>

Config-driven, multi-tenant LiveKit voice agent runtime based on the architecture in [Files_arch.md](./Files_arch.md). The app uses the 2026 LiveKit Agents `AgentServer` + `AgentSession` stack, with cascaded STT -> LLM -> TTS, optional speech-to-speech realtime models, MCP tool servers, adaptive interruption handling, and tool-based agent handoffs.

For the full operational and extension guide, see [TECHNICAL_GUIDE.md](./TECHNICAL_GUIDE.md).

## Project Layout

```text
config/                  tenant YAML, defaults, Pydantic schema
core/                    config loading, session building, pipeline, DB, SIP, telemetry
agents/                  AgentServer entrypoint, triage, specialists, handoffs
tools/                   MCP helpers and custom @function_tool actions
observability/           dashboards and eval suites
```

`config/tenant_config.yaml` is the runtime source of truth. Add tenants, prompts, routing rules, model choices, MCP servers, telephony settings, and observability options there.

## Dev Setup

Install dependencies to a virtual environment:

```console
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set up the environment by copying `.env.example` to `.env.local` and filling in the required values:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `TENANT_ID` (defaults to `acme_corp` in `.env.example`)

The default tenant uses LiveKit Inference descriptors for the cascaded pipeline:

- STT: `deepgram/nova-3:multi`
- LLM: `openai/gpt-5-mini`
- TTS: `cartesia/sonic-3:<voice_id>`

If you switch a tenant to direct provider plugins or to the OpenAI realtime S2S model, set the provider API keys such as `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`, or `CARTESIA_API_KEY`.

You can also do this automatically using the LiveKit CLI:

```bash
lk app env
```

Run the agent:

```console
python main.py dev
```

You can also run the package entrypoint directly:

```console
python -m agents.server dev
```

## Local Test UI

Start the small browser tester:

```console
python ui_server.py
```

Open `http://127.0.0.1:8765`, click **Connect**, allow microphone access, and speak. The UI creates a LiveKit room token, sets room metadata like `{"tenant_id":"acme_corp"}`, and dispatches the configured `LIVEKIT_AGENT_NAME`.

You can also type a message in the transcript panel. Text is sent on the LiveKit `lk.chat` topic, which `AgentSession` handles as frontend text input.

## Tenant Routing

Room metadata can select a tenant:

```json
{"tenant_id": "acme_corp"}
```

Without metadata, the server falls back to `TENANT_ID`. The triage agent reads `agents.routing.rules` from YAML and transfers to `SalesAgent`, `SupportAgent`, or `BillingAgent` with LiveKit's tool-based handoff behavior.

This agent requires a frontend application to communicate with. Use one of the [livekit-examples](https://github.com/livekit-examples/), create your own with the [client quickstarts](https://docs.livekit.io/realtime/quickstarts/), or test against a hosted [Sandbox](https://cloud.livekit.io/projects/p_/sandbox) frontend.

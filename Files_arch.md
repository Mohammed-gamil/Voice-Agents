# LiveKit AI Agents — Scalable & Multi-Tenant Architecture

---

## Executive Summary

Our architecture is a deployable, multi-sellable asset. By coupling LiveKit's cascaded STT→LLM→TTS pipeline with selective Speech-to-Speech (S2S) fast-paths, the system achieves sub-400ms P90 response latency while preserving full debuggability and provider-swap flexibility. The entire runtime — models, prompts, tool sets, pipeline behavior, telephony rules, and tenant isolation — is driven from a single YAML configuration layer, making multi-tenant agency deployments frictionless.

---

## Architecture Overview

### 1. Runtime Model: Worker → Job → Agent → Session

Every deployment instance is structured as a hierarchy of four isolated units:

- **AgentServer / Worker** — The always-on process that registers with LiveKit Cloud or your self-hosted server, advertises capacity via `load_fnc`, and receives job dispatch. Each Worker is a Kubernetes pod; horizontal scaling means adding pods.
- **Job (JobContext)** — A fully isolated task spun up per inbound WebRTC session or SIP call. If a Job crashes, it does not affect any other running Jobs. Each `JobContext` exposes `ctx.room`, `ctx.connect()`, `ctx.api`, and session lifecycle hooks.
- **Agent** — An LLM-powered application object that defines instructions, tools, lifecycle hooks (`on_enter`, `on_exit`), and optionally overrides the session-level model with a per-agent model (e.g. switching a sub-agent to the Realtime API).
- **AgentSession** — The central orchestrator that binds Agent + VAD + STT + LLM + TTS together, manages the voice pipeline, tracks `UserState` / `AgentState`, maintains the global `ChatContext`, and emits observability events. One `AgentSession` manages one user conversation; one `Agent` class can serve many sessions.

### 2. Pipeline Strategy: Hybrid Cascaded + S2S

```
Cascaded (default, production):
  Audio In → VAD → STT → LLM (+ Tools) → TTS → Audio Out

S2S Fast-path (latency-critical simple turns):
  Audio In → Realtime Model (GPT-4o Realtime / Gemini Flash) → Audio Out

Hybrid (config-selectable per tenant or per agent):
  TriageAgent  →  S2S (greeting, simple queries)
                  ↓  handoff on complexity signal
  SpecialistAgent  →  Cascaded (tool calls, CRM writes, reasoning)
```

The cascaded pipeline (VAD → STT → LLM → TTS) is the production default — it delivers transparency, debuggability, and provider-swap flexibility that pure S2S cannot yet match. S2S is reserved as a fast-path for latency-sensitive simple exchanges. The pipeline mode is set in `tenant_config.yaml` under `pipeline.mode` and resolved at `AgentSession` construction time. The abstraction layer (`core/Pipeline/PipelineFactory.py`) reads the config and returns the correct combination of `stt`, `llm`, `tts`, or `realtime` kwargs.

### 3. AgentSession as the Config Surface

All runtime pipeline behavior is expressed through `AgentSession` kwargs sourced from config — nothing is hardcoded:

```python
# core/session_builder.py — generated from tenant_config.yaml
session = AgentSession(
    vad=pipeline.vad,                           # from config: vad.provider
    stt=pipeline.stt,                           # from config: pipeline.stt.*
    llm=pipeline.llm,                           # from config: pipeline.llm.*
    tts=pipeline.tts,                           # from config: pipeline.tts.*
    turn_handling=TurnHandlingOptions(
        interruption=cfg.turn.interruption_mode,       # "vad" | "semantic" | "adaptive"
        min_endpointing_delay=cfg.turn.min_endpointing_delay,
        max_endpointing_delay=cfg.turn.max_endpointing_delay,
        false_interruption_timeout=cfg.turn.false_interruption_timeout,
    ),
    allow_interruptions=cfg.turn.allow_interruptions,
    min_interruption_duration=cfg.turn.min_interruption_duration,
    min_interruption_words=cfg.turn.min_interruption_words,
)
```

`session_builder.py` is the single translation layer between config keys and `AgentSession` constructor kwargs. No model names or pipeline parameters appear anywhere else in the codebase.

### 4. False Interruption Detection

LiveKit v1.5.0+ ships an audio ML model that distinguishes genuine user interruptions from incidental sounds — backchannels ("mm-hmm"), coughs, sighs, and background noise. When a false interruption is detected, the agent automatically resumes playback from where it left off without re-generation. Enabled by setting `turn.interruption_mode: adaptive` in tenant config. Critical for telephony deployments where line noise causes unnecessary agent cutoffs.

### 5. MCP & Tools

MCP is natively supported — a full MCP server integration requires one line of config. Tool sets are entirely config-driven: each tenant YAML declares which MCP servers and which `custom_actions` are active. The `AgentSession` resolves the full tool manifest at Job startup, so new tools are enabled per-tenant without touching agent code.

For irreversible tool calls (database writes, CRM updates), the implementation calls `run_ctx.disallow_interruptions()` to prevent user speech from cancelling mid-execution, and `await context.wait_for_playout()` where the agent must finish speaking before a tool proceeds, we can also add custom phrases like "Please hold while I check that for you."

### 6. Agentic Handoff Pattern

The Handoff Pattern is native to `AgentSession` via `update_agent()`. A lightweight TriageAgent detects intent and transfers the live WebRTC `AgentSession` context to a SpecialistAgent without re-establishing the room connection. Structured conversation summaries are injected into the new agent's `ChatContext` before `on_enter()` fires.

The routing table — which intents map to which SpecialistAgent — lives entirely in `tenant_config.yaml` under `agents.routing.rules`, not in Python logic. Adding a new routing path requires only a YAML change.

### 7. Telephony & SIP Layer

Inbound and outbound calls are managed via LiveKit SIP Trunking. The implementation supports:

- **Cold transfers** — Transfers WebRTC context to another agent Job with no conversation carry-over.
- **Warm transfers to human operators** — Injects a structured `ChatContext` summary into the handoff payload before the human picks up, so operators receive full context without a briefing call.
- **DTMF tone handling** — Config-driven digit-to-intent mappings via `telephony.dtmf_map`.

All SIP trunk credentials, inbound DID numbers, outbound caller IDs, and transfer targets are per-tenant fields in `tenant_config.yaml`.

### 8. Hybrid Database (Abstracted)

The `HybridDB_Client` exposes a unified interface over SQL (relational state, user profiles, conversation history) and VectorDB (semantic search, RAG retrieval). The backend adapters (PostgreSQL, SQLite, pgvector, Pinecone, Weaviate, Qdrant) are config-declared; swapping adapters requires only a YAML change and a migration run — no application code changes.

Schema migrations are Alembic-managed and tenant-scoped, ensuring full data isolation between clients.

### 9. Observability & Distributed Tracing

The system layers three observability tiers:

- **LiveKit Native Telemetry** — `session_usage_updated` events stream per-turn token and cost data. `ChatMessage.metrics` carries per-turn latency (TTFT, E2E). Available with zero additional instrumentation; piped to the tenant's configured observability sink automatically.
- **OpenTelemetry Distributed Traces** — Multi-agent spans across TriageAgent → SpecialistAgent → HumanHandoff. Captures P90/P99 latencies, VAD accuracy, and STT confidence scores. Exporter (Jaeger, Datadog, OTLP) is config-declared per tenant.
- **Automated Evals** — LiveKit's built-in test framework with judge-based pass/fail. Eval suites are per-tenant YAML files defining conversation fixtures and expected outcomes.

Log level is controlled via the `LIVEKIT_LOG_LEVEL` env var — no code changes needed across environments.

### 10. Config-Driven Deployments

The `tenant_config.yaml` is the single source of truth for every behavioral axis of the system. A new tenant onboarding requires only a new YAML block — no Python code changes. A Pydantic schema layer (`config/schema.py`) validates the entire config file at startup and fails fast on any misconfiguration before a single call is handled.

---

## Centralized Configuration Schema (`tenant_config.yaml`)

```yaml
tenants:
  acme_corp:
    display_name: "Acme Corp Assistant"

    # --- Pipeline Mode ---
    pipeline:
      mode: hybrid                    # "cascaded" | "s2s" | "hybrid"
      stt:
        provider: deepgram            # "deepgram" | "assemblyai" | "livekit_inference"
        model: nova-3
        language: multi               # or explicit BCP-47 e.g. "en-US"
      llm:
        provider: openai              # "openai" | "anthropic" | "livekit_inference"
        model: gpt-4.1
        temperature: 0.7
        max_tokens: 1024
      tts:
        provider: cartesia            # "cartesia" | "elevenlabs" | "livekit_inference"
        model: sonic-3
        voice_id: "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
      s2s_model:                      # used when mode=s2s or for hybrid fast-path
        provider: openai_realtime
        model: gpt-4o-realtime-preview
        voice: coral

    # --- Turn Detection & Interruption ---
    turn:
      interruption_mode: adaptive     # "vad" | "semantic" | "adaptive" (ML-based)
      allow_interruptions: true
      min_endpointing_delay: 0.5      # seconds
      max_endpointing_delay: 6.0
      min_interruption_duration: 0.3
      min_interruption_words: 2
      false_interruption_timeout: 1.5

    # --- VAD ---
    vad:
      provider: silero                # "silero" | "webrtc"
      prewarm: true                   # loaded in JobProcess.prewarm hook

    # --- Agents & Routing ---
    agents:
      triage:
        class: TriageAgent
        prompt_key: triage_system     # key into prompts section below
      routing:
        rules:
          - intent: sales
            agent_class: SalesAgent
            prompt_key: sales_system
          - intent: support
            agent_class: SupportAgent
            prompt_key: support_system
          - intent: billing
            agent_class: BillingAgent
            prompt_key: billing_system

    # --- Prompts (all prompts live here, never in Python files) ---
    prompts:
      triage_system: |
        You are a routing assistant for Acme Corp. Detect user intent and
        hand off to the appropriate specialist. Available intents: sales,
        support, billing. Do not attempt to answer questions yourself.
      sales_system: |
        You are a sales assistant for Acme Corp. Your goal is to qualify
        leads and schedule demos. You have access to the CRM and calendar tools.
      support_system: |
        You are a technical support agent for Acme Corp. Resolve issues
        using the knowledge base and ticketing tools.
      billing_system: |
        You are a billing specialist. Handle invoice queries, payment
        issues, and subscription changes via the billing tools.

    # --- Tools ---
    tools:
      mcp_servers:
        - name: crm
          url: "https://crm.acmecorp.internal/mcp"
          enabled: true
        - name: calendar
          url: "https://calendar.acmecorp.internal/mcp"
          enabled: true
      custom_actions:
        - create_ticket
        - update_crm_record
        - send_summary_email

    # --- Telephony ---
    telephony:
      sip_trunk_id: trunk_acme_001
      inbound_did: "+15551234567"
      outbound_caller_id: "+15559876543"
      warm_transfer_target: "+15550001111"  # human operator queue
      dtmf_map:
        "1": sales
        "2": support
        "3": billing

    # --- Database ---
    database:
      sql:
        adapter: postgresql           # "postgresql" | "sqlite"
        schema: acme_corp             # tenant-scoped schema
      vector:
        adapter: pgvector             # "pgvector" | "pinecone" | "qdrant"
        collection: acme_knowledge

    # --- Observability ---
    observability:
      log_level: INFO                 # maps to LIVEKIT_LOG_LEVEL
      otel_exporter: datadog          # "jaeger" | "datadog" | "otlp"
      otel_endpoint: "https://otel.acmecorp.internal"
      emit_session_usage: true        # pipes session_usage_updated to sink
      emit_turn_metrics: true         # pipes ChatMessage.metrics to sink
      eval_suite: acme_evals.yaml
```

---

## File Structure

```
├── config/
│   ├── tenant_config.yaml            # Single source of truth for ALL tenants
│   ├── defaults.yaml                 # Fallback values for any unset tenant key
│   └── schema.py                     # Pydantic model — validates tenant_config.yaml
│                                     # at startup and fails fast on misconfiguration
│
├── core/
│   ├── config_loader.py              # Loads + validates tenant_config.yaml,
│   │                                 # resolves defaults, exposes TenantConfig objects
│   │
│   ├── session_builder.py            # Builds AgentSession from TenantConfig.
│   │                                 # Single place where all pipeline kwargs are set.
│   │                                 # No hardcoded model names anywhere else.
│   │
│   ├── Pipeline/
│   │   ├── PipelineFactory.py        # Returns (stt, llm, tts) OR realtime model
│   │   │                             # based on config pipeline.mode
│   │   └── vad_prewarm.py            # VAD loaded in JobProcess.prewarm hook
│   │
│   ├── Database/
│   │   ├── HybridDB_Client.py        # Unified SQL + VectorDB interface
│   │   ├── adapters/                 # postgresql.py, sqlite.py, pgvector.py,
│   │   │                             # pinecone.py, qdrant.py — swapped via config
│   │   └── migrations/               # Alembic migrations, tenant-scoped schemas
│   │
│   ├── Telephony/
│   │   ├── SIP_Trunking.py           # Inbound/outbound dispatch; credentials from config
│   │   └── Transfers.py              # Warm/cold transfer logic; injects ChatContext
│   │                                 # summary before human handoff
│   │
│   └── Observability/
│       ├── telemetry.py              # Hooks session_usage_updated + ChatMessage.metrics
│       │                             # → routes to configured otel_exporter
│       ├── otel_tracing.py           # OpenTelemetry span management (multi-agent)
│       └── evals/                    # Tenant eval YAML suites + judge harness
│
├── agents/
│   ├── server.py                     # AgentServer entrypoint. Reads tenant ID from
│   │                                 # room metadata → loads TenantConfig →
│   │                                 # calls session_builder → starts AgentSession.
│   │                                 # JobContext prewarm + shutdown hooks live here.
│   │
│   ├── triage/
│   │   └── TriageAgent.py            # Detects intent. Routing table is read from
│   │                                 # config, not hardcoded. Uses update_agent()
│   │                                 # for native session handoff.
│   │
│   ├── specialists/
│   │   ├── SalesAgent.py
│   │   ├── SupportAgent.py
│   │   └── BillingAgent.py           # Each agent reads its prompt via prompt_key
│   │                                 # from config. Tools injected by session_builder.
│   │
│   └── handoff/
│       ├── agent_handoff.py          # Wraps update_agent() with ChatContext summary
│       │                             # injection and structured metadata passing
│       └── human_handoff.py          # Warm transfer: packages summary, triggers SIP
│
├── tools/
│   ├── mcp_servers/                  # MCP server connector definitions; active list
│   │                                 # comes from tenant_config.yaml tools.mcp_servers
│   └── custom_actions/               # @function_tool decorated callables.
│       │                             # disallow_interruptions() on irreversible ops.
│       ├── create_ticket.py
│       ├── update_crm_record.py
│       └── send_summary_email.py
│
└── observability/
    ├── dashboards/                   # Grafana / Datadog dashboard templates
    └── evals/                        # Per-tenant YAML eval suites
        └── acme_evals.yaml
```

---

## Deployment Notes

**Tenant resolution** — The `AgentServer` reads the tenant identifier from LiveKit room metadata (set by the frontend or SIP dispatch rules) at `entrypoint`. This resolves the correct `TenantConfig` block without requiring per-tenant Worker processes — one Worker fleet serves all tenants.

**Horizontal scaling** — Scale by adding Worker pods. The `load_fnc` in `server.py` controls when a Worker accepts new Jobs based on current concurrency. No sticky sessions required; LiveKit handles routing.

**Model hot-swap** — Changing any model for any tenant requires only a YAML edit and a rolling restart (or a live config-reload hook). No code deployments.

**New tenant onboarding** — Add a block to `tenant_config.yaml`, define prompts and tool enable-list, run `alembic upgrade head --schema <tenant_id>`. Zero code changes.

**LiveKit Cloud vs self-hosted** — Identical application code across both. Only `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` env vars differ. LiveKit Cloud adds managed built-in observability (transcripts and traces) supplementary to the custom pipeline above.

**Provider lock-in** — Using `provider: livekit_inference` in the pipeline config routes all model calls through LiveKit's unified inference API, eliminating direct provider key management and enabling zero-code provider swaps at the infrastructure level.
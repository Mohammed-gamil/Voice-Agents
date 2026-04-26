from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PipelineMode = Literal["cascaded", "s2s", "hybrid"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class STTConfig(StrictModel):
    provider: Literal["deepgram", "assemblyai", "livekit_inference"] = "livekit_inference"
    model: str = "deepgram/nova-3"
    language: str = "multi"


class LLMConfig(StrictModel):
    provider: Literal["openai", "anthropic", "livekit_inference"] = "livekit_inference"
    model: str = "openai/gpt-5-mini"
    temperature: float = 0.7
    max_tokens: int | None = 1024


class TTSConfig(StrictModel):
    provider: Literal["openai", "cartesia", "elevenlabs", "livekit_inference"] = "livekit_inference"
    model: str = "cartesia/sonic-3"
    voice_id: str = "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"


class RealtimeModelConfig(StrictModel):
    provider: Literal["openai_realtime", "google_realtime", "xai_realtime"] = "openai_realtime"
    model: str = "gpt-realtime"
    voice: str = "marin"
    modalities: list[str] = Field(default_factory=lambda: ["text", "audio"])


class PipelineConfig(StrictModel):
    mode: PipelineMode = "cascaded"
    production_confirmed: bool = False
    stt: STTConfig = Field(default_factory=STTConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    s2s_model: RealtimeModelConfig | None = Field(default_factory=RealtimeModelConfig)


class TurnConfig(StrictModel):
    interruption_mode: Literal["vad", "adaptive"] = "adaptive"
    turn_detection: Literal["vad", "stt", "realtime_llm", "manual"] | None = None
    allow_interruptions: bool = True
    min_endpointing_delay: float = 0.5
    max_endpointing_delay: float = 6.0
    min_interruption_duration: float = 0.5
    min_interruption_words: int = 0
    false_interruption_timeout: float | None = 2.0
    resume_false_interruption: bool = True
    preemptive_generation: bool = False


class VADConfig(StrictModel):
    provider: Literal["silero", "webrtc", "none"] = "silero"
    prewarm: bool = True


class AgentRefConfig(StrictModel):
    class_name: str = Field(alias="class")
    prompt_key: str


class RoutingRule(StrictModel):
    intent: str
    agent_class: str
    prompt_key: str


class RoutingConfig(StrictModel):
    rules: list[RoutingRule] = Field(default_factory=list)


class AgentsConfig(StrictModel):
    triage: AgentRefConfig
    routing: RoutingConfig = Field(default_factory=RoutingConfig)


class MCPServerConfig(StrictModel):
    name: str
    url: str
    enabled: bool = True
    allowed_tools: list[str] | None = None
    headers: dict[str, str] | None = None


class HTTPServiceConfig(StrictModel):
    enabled: bool = False
    url: str | None = None
    method: Literal["POST", "PUT", "PATCH"] = "POST"
    headers: dict[str, str] = Field(default_factory=dict)
    auth_token_env: str | None = None
    timeout_seconds: float = 10.0


class EmailServiceConfig(StrictModel):
    enabled: bool = False
    provider: Literal["smtp"] = "smtp"
    smtp_host: str | None = None
    smtp_port: int = 587
    username_env: str | None = "SMTP_USERNAME"
    password_env: str | None = "SMTP_PASSWORD"
    from_email: str | None = None
    use_tls: bool = True


class ToolIntegrationConfig(StrictModel):
    ticketing: HTTPServiceConfig = Field(default_factory=HTTPServiceConfig)
    crm: HTTPServiceConfig = Field(default_factory=HTTPServiceConfig)
    email: EmailServiceConfig = Field(default_factory=EmailServiceConfig)


class ToolsConfig(StrictModel):
    mcp_servers: list[MCPServerConfig] = Field(default_factory=list)
    custom_actions: list[str] = Field(default_factory=list)
    integrations: ToolIntegrationConfig = Field(default_factory=ToolIntegrationConfig)


class ScenarioConfig(StrictModel):
    description: str
    instructions: str


class ConversationConfig(StrictModel):
    greetings: dict[str, str] = Field(default_factory=dict)
    tool_messages: dict[str, str] = Field(default_factory=dict)
    scenarios: dict[str, ScenarioConfig] = Field(default_factory=dict)


class TelephonyConfig(StrictModel):
    sip_trunk_id: str | None = None
    inbound_did: str | None = None
    outbound_caller_id: str | None = None
    warm_transfer_target: str | None = None
    dtmf_map: dict[str, str] = Field(default_factory=dict)


class SQLConfig(StrictModel):
    adapter: Literal["postgresql", "sqlite"] = "sqlite"
    schema_name: str = Field(default="public", alias="schema")
    dsn: str | None = None


class VectorConfig(StrictModel):
    adapter: Literal["pgvector", "pinecone", "qdrant", "none"] = "none"
    collection: str | None = None


class DatabaseConfig(StrictModel):
    sql: SQLConfig = Field(default_factory=SQLConfig)
    vector: VectorConfig = Field(default_factory=VectorConfig)


class ObservabilityConfig(StrictModel):
    log_level: str = "INFO"
    otel_exporter: Literal["jaeger", "datadog", "otlp", "none"] = "none"
    otel_endpoint: str | None = None
    emit_session_usage: bool = True
    emit_turn_metrics: bool = True
    eval_suite: str | None = None


class TenantConfig(StrictModel):
    tenant_id: str = ""
    display_name: str
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    turn: TurnConfig = Field(default_factory=TurnConfig)
    vad: VADConfig = Field(default_factory=VADConfig)
    agents: AgentsConfig
    prompts: dict[str, str]
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    telephony: TelephonyConfig = Field(default_factory=TelephonyConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

    @field_validator("prompts")
    @classmethod
    def prompts_must_not_be_empty(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("at least one prompt must be configured")
        return value

    def prompt(self, key: str) -> str:
        try:
            return self.prompts[key]
        except KeyError as exc:
            raise KeyError(f"prompt '{key}' is not configured for tenant '{self.tenant_id}'") from exc


class TenantConfigFile(StrictModel):
    tenants: dict[str, TenantConfig]


RawConfig = dict[str, Any]

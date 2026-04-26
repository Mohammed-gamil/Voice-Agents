# Changelog

All notable project changes will be documented in this file.

## Unreleased

### Added

- Restructured the project into a multi-tenant LiveKit voice-agent architecture.
- Added `AgentServer` runtime entrypoint in `agents/server.py`.
- Added tenant config loading and validation with Pydantic models.
- Added default and tenant YAML config files.
- Added centralized `AgentSession` construction in `core/session_builder.py`.
- Added pipeline construction for VAD, STT, LLM, TTS, LiveKit Inference descriptors, and lazy realtime configuration.
- Added triage and specialist agents:
  - `TriageAgent`
  - `SalesAgent`
  - `SupportAgent`
  - `BillingAgent`
- Added tool-based agent handoff helpers.
- Added custom action registry and starter tools:
  - `create_ticket`
  - `update_crm_record`
  - `send_summary_email`
- Added configurable greetings, scenarios, and tool progress phrases.
- Added `speak_tool_progress()` helper so tools can speak wait phrases before long-running or irreversible actions.
- Added observability, database, and telephony scaffold modules.
- Added local browser test UI under `web/`.
- Added `ui_server.py` to serve the test UI and generate LiveKit room tokens.
- Added `TECHNICAL_GUIDE.md` with setup, runtime, extension, testing, and troubleshooting guidance.
- Added `TODO.md` for implementation follow-up work.

### Changed

- Replaced the original single-file story-editor demo with a tenant-driven voice-agent runtime.
- Updated `main.py` to delegate to `agents.server`.
- Updated dependencies to the LiveKit Agents `1.5.6` generation with MCP support.
- Updated `.env.example` with tenant, agent, and provider-key settings.
- Expanded `README.md` to describe the project layout and local UI workflow.
- Updated `.gitignore` to ignore local log files.

### Notes

- `livekit` is pinned to `1.1.5` because `livekit-agents==1.5.6` currently declares that exact dependency.
- Hybrid realtime model construction is lazy so cascaded tenants do not need realtime provider credentials unless realtime mode is actually used.

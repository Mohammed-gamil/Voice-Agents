# LiveKit Modernization Design

**Date:** 2026-04-26
**Topic:** LiveKit Agents Best Practices & Modernization

## Overview
This document specifies the architectural changes required to bring the current voice agent project up to LiveKit Agents 1.5.6 standards, leveraging the latest research and best practices from the last 30 days. The goal is to eliminate deprecated patterns, improve concurrency performance, implement robust safety guardrails, and prepare the agent for multimodal interactions.

## 1. Architecture & Transport (VoicePipelineAgent)
- **Current State:** The application subclasses `Agent` and uses the older `AgentSession` approach with explicit `session.generate_reply()` calls in `agents/base.py`.
- **New Design:** We will migrate to `VoicePipelineAgent`, which is the canonical architecture for orchestrating VAD, STT, LLM, and TTS plugins.
- **Turn Detection:** The traditional `silero.VAD` initialization in `core/Pipeline/PipelineFactory.py` will be replaced by or augmented with Semantic Turn Detection to better handle interruptions and noisy environments.
- **MCP Integration:** Ensure that `MCPServerHTTP` (using SSE) is passed to the `mcp_servers` configuration of the `VoicePipelineAgent` to enable dynamic tool discovery for the voice agent.

## 2. Database & Performance (asyncpg)
- **Current State:** `requirements.txt` specifies `asyncpg>=0.30,<1`.
- **New Design:** Bump `asyncpg` to `>=0.31.0,<1` in `requirements.txt` to eliminate concurrency and tracing performance bottlenecks reported in high-throughput real-time (RTC) asyncio loops.
- **Application Logic:** The `HybridDBClient` will maintain its interface but will benefit directly from the `asyncpg` 0.31.0 optimizations underneath the `PostgresAdapter`.

## 3. Safety & Observability (Observer-Pattern)
- **Current State:** Single LLM in the loop providing real-time responses.
- **New Design:** Implement an "Observer LLM" pattern.
- **Mechanism:** A secondary, asynchronous background task (the "Observer") will subscribe to the conversation's `ChatContext` transcript. It will evaluate user inputs and agent responses for safety and compliance. If it detects an issue, it will inject corrective context directly into the main `ChatContext` or trigger a graceful handover/termination without adding latency to the main real-time response loop.

## 4. Multimodal Support (Vision Tracks)
- **Current State:** Primarily audio and text.
- **New Design:** Update `build_realtime` and LLM builders in `PipelineFactory.py` to enable the vision modality (`modalities=["text", "audio", "image"]`) when supported (e.g., Gemini Live, GPT-4o Realtime).
- **Video Input:** The agent session setup will be configured to accept video tracks alongside audio tracks so the LLM can "see" screen shares or camera feeds.

## Error Handling & Testing
- Ensure the Observer LLM handles rate limits gracefully so it doesn't crash the main session.
- Add tests confirming that `VoicePipelineAgent` connects to MCP servers without blocking startup.
- Validate that `generate_reply` is completely removed from the codebase to avoid duplex continuation failures.

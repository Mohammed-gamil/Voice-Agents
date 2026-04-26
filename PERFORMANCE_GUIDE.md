# Voice AI Performance & Optimization Guide

This project is optimized for "zero-latency" feel and high-concurrency efficiency. This guide explains the software-level optimizations implemented.

## 1. Zero-Latency Configuration
The project uses a `ConfigManager` singleton that eliminates disk I/O from the critical session path.

*   **In-Memory Caching:** Configurations are parsed and validated once into RAM. `load_tenant_config()` is an **O(1)** memory lookup (< 0.1ms).
*   **Hot-Reloading:** Uses `watchdog` to monitor `config/tenant_config.yaml`. Updates are merged in the background. If a file is saved with errors, the system continues using the last-known-good config, ensuring zero downtime.

## 2. Modern Agent Architecture
We have migrated from the legacy `Agent` class to `VoicePipelineAgent`.

*   **Canonical Transport:** Replaces deprecated `generate_reply` (duplex) patterns with the robust `VoicePipelineAgent` loop, preventing continuation failures and audio glitches.
*   **Semantic Turn Detection:** Replaces simple VAD with transformer-based turn detection. It intelligently distinguishes between background noise and intentional "barge-in," making the agent feel more human.
*   **Observer Pattern:** Implements an asynchronous `ObserverAgent` task. This performs safety checks and context injection without blocking the primary voice loop, maintaining high FPS (Frames Per Second) for the audio pipeline.

## 3. Database Efficiency
*   **asyncpg 0.31.0:** Upgraded to the latest performance-tuned version of `asyncpg`. This fixed known latency spikes in high-concurrency `asyncio` loops used for real-time audio.
*   **Connection Pooling:** The `PostgresAdapter` is tuned to handle the rapid open/close cycles of voice sessions.

## 4. Code Best Practices for Speed
1.  **Lazy Imports Removed:** Core plugins (Silero, Deepgram, OpenAI) are moved to a module-level cache to ensure no import-overhead happens during the user's join event.
2.  **Pre-warming:** The server runs a `setup_fnc` during bootstrap to load the VAD models into memory, eliminating the "cold start" penalty for the first caller.
3.  **Process-Level Workers:** The server is configured to spawn full OS processes for each job, circumventing the Python GIL and utilizing all available CPU cores.

## How to Maintain Peak Performance
*   Keep `modalities` set to `["text", "audio"]` unless vision is explicitly required.
*   Monitor `ObserverAgent` logs for long-running safety checks; keep them lightweight.
*   Ensure environment variables for integrations (CRM, Ticketing) are resolved correctly by the new interpolation engine to avoid runtime lookup failures.

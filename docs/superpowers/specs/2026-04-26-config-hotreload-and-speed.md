# Phase 3: In-Memory Caching & Hot-Reloading for Peak Performance

**Date:** 2026-04-26
**Topic:** Configurability & Performance Optimization

## Overview
This document specifies the third and final phase of configuration enhancements. The primary goal is to eliminate configuration-related latency during session initialization while allowing for dynamic updates without server restarts.

## 1. Speed Optimization: In-Memory Caching
- **Problem:** Currently, `load_tenant_config` hits the disk and runs Pydantic validation on every session start.
- **Solution:** Implement a `ConfigManager` singleton that maintains a cache of `TenantConfig` objects.
- **Access Pattern:** `load_tenant_config(id)` becomes a simple dictionary lookup, removing disk I/O and CPU-heavy validation from the "time to first word" path.

## 2. Dynamic Updates: Hot-Reloading (`watchdog`)
- **Mechanism:** Integrate the `watchdog` library to subscribe to OS-level file system events.
- **Monitoring:** A background observer will track `config/tenant_config.yaml`.
- **Atomic Swap:** When the file is modified:
  1. The manager reads and validates the *entire* file in the background.
  2. If validation is successful, the manager swaps the in-memory cache reference.
  3. If validation fails (e.g., YAML syntax error or schema violation), the error is logged, and the manager **must** continue serving the last-known-good configuration.
- **Deployment:** This is highly efficient on Ubuntu (Linux) using `inotify`.

## 3. Implementation Details (`core/config_loader.py`)
- Refactor `load_all_tenants` to be internal or managed by the singleton.
- Add `ConfigManager.start_watching()` to be called during server bootstrap in `agents/server.py`.
- Ensure thread safety during the reference swap using a simple `threading.Lock` if necessary, though pointer swaps are typically atomic in Python.

## 4. Validation and Testing (`tests/test_config_hotreload.py`)
- **Latency Benchmark:** (Manual/Observability) Verify that `load_tenant_config` execution time drops to <1ms.
- **Hot-Reload Test:** Update the YAML file and verify that a subsequent `load_tenant_config` call returns the updated value without a restart.
- **Failure Recovery Test:** Inject an invalid YAML into the file and verify the system continues to function using the previous valid state.

## 5. Scope Check and Ambiguity Review
- **Scope:** Includes caching, `watchdog` integration, and background thread management.
- **Ambiguity:** What happens to active sessions? They will continue using the `TenantConfig` object they were initialized with (as they hold a direct reference), while new sessions will pick up the new object. This is the desired behavior.

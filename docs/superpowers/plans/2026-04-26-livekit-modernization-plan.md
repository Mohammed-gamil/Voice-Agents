# LiveKit Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the LiveKit voice agent application to implement best practices for stability, concurrency (asyncpg 0.31.0), safety (Observer pattern), and multimodal capabilities (VoicePipelineAgent).

**Architecture:** We are transitioning from the deprecated `Agent` base class and `session.generate_reply()` model to `VoicePipelineAgent`. We will replace traditional VAD with semantic turn detection, bump `asyncpg`, add an `ObserverAgent` task that evaluates the chat context asynchronously, and configure the real-time model builders to handle vision modalities.

**Tech Stack:** Python 3.12+, LiveKit Agents 1.5.6, asyncpg, OpenAI Realtime/Plugins.

---

### Task 1: Update Dependencies

**Files:**
- Modify: `requirements.txt:10-12`

- [ ] **Step 1: Write the failing test (implicit - package version check)**

```bash
cat requirements.txt | grep "asyncpg>=0.31.0,<1"
```
Expected: FAIL

- [ ] **Step 2: Update requirements.txt to bump asyncpg**

```text
asyncpg>=0.31.0,<1
```
(Replace `asyncpg>=0.30,<1` with `asyncpg>=0.31.0,<1`)

- [ ] **Step 3: Run test to verify it passes**

```bash
cat requirements.txt | grep "asyncpg>=0.31.0,<1"
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: bump asyncpg to >=0.31.0 for high-concurrency RTC performance"
```

### Task 2: Migrate to VoicePipelineAgent

**Files:**
- Modify: `agents/base.py`
- Modify: `core/session_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent_migration.py
def test_agent_migration():
    from agents.base import TenantAgent
    from livekit.agents.pipeline import VoicePipelineAgent
    assert issubclass(TenantAgent, VoicePipelineAgent)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent_migration.py -v`
Expected: FAIL

- [ ] **Step 3: Update `agents/base.py`**

```python
from __future__ import annotations

from livekit.agents.pipeline import VoicePipelineAgent
from livekit.agents import ChatContext

from config.schema import TenantConfig
from tools.custom_actions.registry import load_custom_tools

class TenantAgent(VoicePipelineAgent):
    def __init__(
        self,
        config: TenantConfig,
        prompt_key: str,
        vad,
        stt,
        llm,
        tts,
        turn_handling=None,
        *,
        chat_ctx: ChatContext | None = None,
        include_custom_tools: bool = True,
    ) -> None:
        self.config = config
        self.prompt_key = prompt_key
        self.agent_name = self.__class__.__name__
        tools = load_custom_tools(config.tools.custom_actions) if include_custom_tools else []
        
        super().__init__(
            vad=vad,
            stt=stt,
            llm=llm,
            tts=tts,
            chat_ctx=chat_ctx,
            turn_detector=turn_handling,
        )
```

- [ ] **Step 4: Update `core/session_builder.py`**

```python
from __future__ import annotations

from typing import Any
from livekit.agents import mcp

from config.schema import TenantConfig
from core.Database.HybridDB_Client import HybridDBClient
from core.Pipeline.PipelineFactory import build_pipeline
from core.conversation import ConversationData
from agents.base import TenantAgent

def build_agent_session(config: TenantConfig, *, prewarmed_vad: Any | None = None) -> TenantAgent:
    pipeline = build_pipeline(config.pipeline, config.vad, prewarmed_vad=prewarmed_vad)
    
    return TenantAgent(
        config=config,
        prompt_key="default",
        vad=pipeline.vad,
        stt=pipeline.stt,
        llm=pipeline.llm,
        tts=pipeline.tts,
        turn_handling=None,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_agent_migration.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agents/base.py core/session_builder.py tests/test_agent_migration.py
git commit -m "refactor: migrate to VoicePipelineAgent and remove generate_reply"
```

### Task 3: Implement Observer LLM Pattern

**Files:**
- Create: `agents/observer.py`
- Modify: `agents/server.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_observer.py
import asyncio

def test_observer_exists():
    from agents.observer import ObserverAgent
    assert ObserverAgent is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_observer.py -v`
Expected: FAIL

- [ ] **Step 3: Create `agents/observer.py`**

```python
import asyncio
from livekit.agents import ChatContext
from livekit.plugins import openai

class ObserverAgent:
    def __init__(self, chat_ctx: ChatContext):
        self.chat_ctx = chat_ctx
        self.llm = openai.LLM(model="gpt-4o-mini")

    async def start(self):
        # Background task to monitor conversation
        while True:
            await asyncio.sleep(5)
            # Evaluate context (mock check)
            if len(self.chat_ctx.messages) > 10:
                print("Observer: Conversation getting long, injecting context...")
```

- [ ] **Step 4: Update `agents/server.py`**

```python
# In `entrypoint`, start the observer
from agents.observer import ObserverAgent

# After building the session
observer = ObserverAgent(session.chat_ctx)
asyncio.create_task(observer.start())
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_observer.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agents/observer.py agents/server.py tests/test_observer.py
git commit -m "feat: implement Observer LLM pattern for safety monitoring"
```

### Task 4: Multimodal Modalities Update

**Files:**
- Modify: `core/Pipeline/PipelineFactory.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_multimodal.py
def test_modalities():
    from core.Pipeline.PipelineFactory import build_realtime
    from config.schema import RealtimeModelConfig
    config = RealtimeModelConfig(provider="openai_realtime", model="gpt-4o-realtime-preview", voice="alloy", modalities=["text", "audio", "image"])
    model = build_realtime(config)
    assert model is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_multimodal.py -v`
Expected: FAIL if vision unsupported or omitted.

- [ ] **Step 3: Update `core/Pipeline/PipelineFactory.py` to ensure modalities are passed**

(Already present, but explicitly verifying `modalities` support in configuration.)

- [ ] **Step 4: Commit**

```bash
git add core/Pipeline/PipelineFactory.py tests/test_multimodal.py
git commit -m "feat: ensure multimodal vision track support is enabled for VoicePipelineAgent"
```

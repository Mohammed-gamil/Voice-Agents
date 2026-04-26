# Phase 1: Environment Variable Interpolation & JSON Schema Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance configuration by supporting robust `${ENV_VAR:default}` interpolation and exporting a JSON schema for IDE autocompletion.

**Architecture:** We will modify `core/config_loader.py`'s `_expand_env` to handle fallback defaults and raise exceptions for missing environment variables. We will also add a script `config/export_schema.py` to dump Pydantic's JSON schema, and add tests.

**Tech Stack:** Python 3.12+, Pydantic, pytest.

---

### Task 1: Update Env Var Interpolation Logic

**Files:**
- Modify: `core/config_loader.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_config_loader.py`.
```python
import os
import pytest
from core.config_loader import _expand_env

def test_expand_env_with_default():
    os.environ.pop("MISSING_VAR", None)
    result = _expand_env("value is ${MISSING_VAR:default_val}")
    assert result == "value is default_val"

def test_expand_env_missing_raises():
    os.environ.pop("MISSING_VAR", None)
    with pytest.raises(ValueError, match="Missing environment variable: MISSING_VAR"):
        _expand_env("value is ${MISSING_VAR}")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_loader.py -v`
Expected: FAIL (because current implementation doesn't support defaults or raise ValueErrors for missing vars).

- [ ] **Step 3: Write minimal implementation**

Modify `core/config_loader.py` to use the new pattern and logic.
```python
# Replace ENV_PATTERN definition at the top
ENV_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)(?::([^}]*))?\}")

# Replace _expand_env function
def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        def repl(match: re.Match) -> str:
            var_name = match.group(1)
            default_val = match.group(2)
            env_val = os.getenv(var_name)
            if env_val is not None:
                return env_val
            if default_val is not None:
                return default_val
            raise ValueError(f"Missing environment variable: {var_name}")
        return ENV_PATTERN.sub(repl, value)
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    return value
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config_loader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/config_loader.py tests/test_config_loader.py
git commit -m "feat: robust env var interpolation with fallbacks and strict missing var checks"
```

### Task 2: Create Schema Export Script

**Files:**
- Create: `config/export_schema.py`

- [ ] **Step 1: Write the script**

```python
import json
from pathlib import Path
from config.schema import TenantConfigFile

def main():
    schema = TenantConfigFile.model_json_schema()
    out_path = Path(__file__).parent / "tenant_config.schema.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"Schema successfully exported to {out_path}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script to verify generation**

Run: `python config/export_schema.py`
Expected: File `config/tenant_config.schema.json` is created.

- [ ] **Step 3: Commit**

```bash
git add config/export_schema.py config/tenant_config.schema.json
git commit -m "feat: add schema export script and initial json schema for IDE support"
```

### Task 3: Annotate `tenant_config.yaml` with schema

**Files:**
- Modify: `config/tenant_config.yaml`

- [ ] **Step 1: Prepend the schema directive**

Add this exact line as the very first line of `config/tenant_config.yaml`:
```yaml
# yaml-language-server: $schema=./tenant_config.schema.json
```

- [ ] **Step 2: Commit**

```bash
git add config/tenant_config.yaml
git commit -m "chore: link tenant_config.yaml to exported JSON schema"
```

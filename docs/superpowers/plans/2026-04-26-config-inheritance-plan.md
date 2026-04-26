# Phase 2: Recursive Configuration Inheritance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement multi-level configuration inheritance with support for additive list merging via markers.

**Architecture:** Update Pydantic schema to support `extends`. Rewrite `_deep_merge` to support the `{ "append": [...] }` marker. Implement a recursive resolver in `config_loader.py` that builds the final raw dictionary from the inheritance chain (Defaults -> Root -> Parent -> Child) while detecting cycles.

**Tech Stack:** Python 3.12+, Pydantic, pytest.

---

### Task 1: Update Schema with `extends`

**Files:**
- Modify: `config/schema.py`

- [ ] **Step 1: Add `extends` field to `TenantConfig`**

```python
# In config/schema.py, inside TenantConfig class
    extends: str | None = None
```

- [ ] **Step 2: Commit**

```bash
git add config/schema.py
git commit -m "feat: add extends field to TenantConfig schema"
```

### Task 2: Enhance `_deep_merge` for List Markers

**Files:**
- Modify: `core/config_loader.py`

- [ ] **Step 1: Update `_deep_merge` logic**

```python
def _deep_merge(base: RawConfig, override: RawConfig) -> RawConfig:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        # Check for list append marker
        if isinstance(value, dict) and "append" in value and len(value) == 1:
            append_val = value["append"]
            if not isinstance(append_val, list):
                raise ValueError(f"Marker 'append' for key '{key}' must contain a list.")
            base_list = merged.get(key, [])
            if not isinstance(base_list, list):
                base_list = [] # Fallback if parent wasn't a list
            merged[key] = base_list + copy.deepcopy(append_val)
        elif isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged
```

- [ ] **Step 2: Commit**

```bash
git add core/config_loader.py
git commit -m "feat: support additive list merging via {'append': [...]} marker in deep_merge"
```

### Task 3: Implement Recursive Resolver

**Files:**
- Modify: `core/config_loader.py`

- [ ] **Step 1: Implement `_resolve_inheritance`**

```python
def _resolve_inheritance(
    tenant_id: str,
    all_raw: dict[str, Any],
    defaults: RawConfig,
    seen: set[str] | None = None
) -> RawConfig:
    if seen is None:
        seen = set()
    
    if tenant_id in seen:
        chain = " -> ".join(list(seen) + [tenant_id])
        raise ValueError(f"Circular inheritance detected: {chain}")
    
    seen.add(tenant_id)
    
    raw_config = all_raw.get(tenant_id)
    if raw_config is None:
        raise KeyError(f"Parent tenant '{tenant_id}' not found in configuration.")
    
    parent_id = raw_config.get("extends")
    
    # Base case: no inheritance or root of chain
    if not parent_id:
        return _deep_merge(defaults, raw_config)
    
    # Recursive case: merge child into resolved parent
    parent_resolved = _resolve_inheritance(parent_id, all_raw, defaults, seen)
    return _deep_merge(parent_resolved, raw_config)
```

- [ ] **Step 2: Update `load_all_tenants` to use resolver**

```python
def load_all_tenants(
    tenants_path: Path = TENANTS_PATH,
    defaults_path: Path = DEFAULTS_PATH,
) -> dict[str, TenantConfig]:
    defaults = _read_yaml(defaults_path)
    raw_file = _read_yaml(tenants_path)
    raw_tenants = raw_file.get("tenants", {})
    
    resolved_tenants: dict[str, Any] = {}
    for tenant_id in raw_tenants:
        # Resolve inheritance for each tenant
        resolved = _resolve_inheritance(tenant_id, raw_tenants, defaults)
        # Ensure tenant_id is preserved
        resolved["tenant_id"] = tenant_id
        resolved_tenants[tenant_id] = resolved

    return TenantConfigFile(tenants=resolved_tenants).tenants
```

- [ ] **Step 3: Commit**

```bash
git add core/config_loader.py
git commit -m "feat: recursive inheritance resolution with cycle detection"
```

### Task 4: Add Inheritance Tests

**Files:**
- Modify: `tests/test_config_loader.py`

- [ ] **Step 1: Add test cases**

```python
def test_inheritance_basic():
    from core.config_loader import _resolve_inheritance
    raw = {
        "base": {"display_name": "Base"},
        "child": {"extends": "base"}
    }
    resolved = _resolve_inheritance("child", raw, {})
    assert resolved["display_name"] == "Base"

def test_inheritance_list_append():
    from core.config_loader import _resolve_inheritance
    raw = {
        "base": {"tools": {"custom_actions": ["a1"]}},
        "child": {"extends": "base", "tools": {"custom_actions": {"append": ["a2"]}}}
    }
    resolved = _resolve_inheritance("child", raw, {})
    assert resolved["tools"]["custom_actions"] == ["a1", "a2"]

def test_inheritance_cycle_raises():
    from core.config_loader import _resolve_inheritance
    raw = {
        "a": {"extends": "b"},
        "b": {"extends": "a"}
    }
    with pytest.raises(ValueError, match="Circular inheritance"):
        _resolve_inheritance("a", raw, {})
```

- [ ] **Step 2: Run tests**

Run: `$env:PYTHONPATH="."; pytest tests/test_config_loader.py`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_config_loader.py
git commit -m "test: verify config inheritance and list markers"
```

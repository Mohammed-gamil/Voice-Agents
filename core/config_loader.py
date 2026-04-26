from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import Any

import yaml

from config.schema import RawConfig, TenantConfig, TenantConfigFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULTS_PATH = PROJECT_ROOT / "config" / "defaults.yaml"
TENANTS_PATH = PROJECT_ROOT / "config" / "tenant_config.yaml"
ENV_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)(?::([^}]*))?\}")


def _read_yaml(path: Path) -> RawConfig:
    if not path.exists():
        raise FileNotFoundError(f"configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


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
                base_list = []  # Fallback if parent wasn't a list
            merged[key] = base_list + copy.deepcopy(append_val)
        elif isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


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


def load_all_tenants(
    tenants_path: Path = TENANTS_PATH,
    defaults_path: Path = DEFAULTS_PATH,
) -> dict[str, TenantConfig]:
    defaults = _read_yaml(defaults_path)
    raw_tenants = _read_yaml(tenants_path)
    tenants = raw_tenants.get("tenants", {})
    merged: dict[str, Any] = {"tenants": {}}

    for tenant_id, tenant_config in tenants.items():
        resolved = _expand_env(_deep_merge(defaults, tenant_config or {}))
        resolved["tenant_id"] = tenant_id
        merged["tenants"][tenant_id] = resolved

    return TenantConfigFile.model_validate(merged).tenants


def load_tenant_config(tenant_id: str | None = None) -> TenantConfig:
    tenants = load_all_tenants()
    resolved_id = tenant_id or next(iter(tenants), None)
    if not resolved_id:
        raise RuntimeError("no tenants are configured")
    try:
        return tenants[resolved_id]
    except KeyError as exc:
        known = ", ".join(sorted(tenants))
        raise KeyError(f"unknown tenant '{resolved_id}'. Configured tenants: {known}") from exc

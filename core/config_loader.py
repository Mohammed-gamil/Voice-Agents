from __future__ import annotations

import copy
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any

import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config.schema import RawConfig, TenantConfig, TenantConfigFile


logger = logging.getLogger("config-loader")

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


def _resolve_inheritance(
    tenant_id: str,
    all_raw: dict[str, Any],
    defaults: RawConfig,
    seen: set[str] | None = None,
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


def _load_all_tenants_raw(
    tenants_path: Path = TENANTS_PATH,
    defaults_path: Path = DEFAULTS_PATH,
) -> dict[str, TenantConfig]:
    defaults = _read_yaml(defaults_path)
    raw_file = _read_yaml(tenants_path)
    raw_tenants = raw_file.get("tenants", {})

    resolved_tenants: dict[str, Any] = {}
    for tenant_id in raw_tenants:
        resolved = _resolve_inheritance(tenant_id, raw_tenants, defaults)
        resolved = _expand_env(resolved)
        resolved["tenant_id"] = tenant_id
        resolved_tenants[tenant_id] = resolved

    return TenantConfigFile(tenants=resolved_tenants).tenants


class ConfigManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._tenants: dict[str, TenantConfig] = {}
        self._observer = None
        self.reload()

    @classmethod
    def instance(cls) -> ConfigManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def reload(self) -> None:
        """Reloads the configuration from disk and validates it."""
        try:
            new_tenants = _load_all_tenants_raw()
            with self._lock:
                self._tenants = new_tenants
            logger.info("Configuration loaded successfully.")
        except Exception as e:
            logger.error(f"Error reloading configuration: {e}. Keeping previous valid state.")
            if not self._tenants:
                raise

    def get_tenant(self, tenant_id: str | None = None) -> TenantConfig:
        """Returns a cached tenant configuration."""
        with self._lock:
            tenants = self._tenants
        
        if not tenants:
            raise RuntimeError("no tenants are configured")
            
        resolved_id = tenant_id or next(iter(tenants), None)
        try:
            return tenants[resolved_id]
        except KeyError as exc:
            known = ", ".join(sorted(tenants))
            raise KeyError(f"unknown tenant '{resolved_id}'. Configured tenants: {known}") from exc

    def start_watching(self) -> None:
        """Starts a background thread to watch for configuration changes."""
        if self._observer:
            return

        manager = self
        class ReloadHandler(FileSystemEventHandler):
            def on_modified(self, event):
                if Path(event.src_path).resolve() == TENANTS_PATH.resolve():
                    logger.info("Configuration file change detected. Reloading...")
                    manager.reload()

        self._observer = Observer()
        self._observer.schedule(ReloadHandler(), path=str(TENANTS_PATH.parent), recursive=False)
        self._observer.start()
        logger.info(f"Started config file watcher on {TENANTS_PATH}")


def load_tenant_config(tenant_id: str | None = None) -> TenantConfig:
    """Proxy to the cached ConfigManager instance."""
    return ConfigManager.instance().get_tenant(tenant_id)


def load_all_tenants() -> dict[str, TenantConfig]:
    """Returns all cached tenant configurations."""
    return ConfigManager.instance()._tenants

# Phase 1: Environment Variable Interpolation & JSON Schema Generation

**Date:** 2026-04-26
**Topic:** Configurability Enhancements

## Overview
This document specifies the first phase of enhancing the project's configuration system. The goal is to provide robust environment variable resolution across all string values in `tenant_config.yaml` and to generate a JSON schema that enables IDE autocompletion for operators managing the configurations.

## 1. Env Var Interpolation (`core/config_loader.py`)

**Mechanism:**
- Before Pydantic validation runs, the raw dictionary parsed from `tenant_config.yaml` will be recursively traversed.
- Any string matching the regular expression `\$\{([A-Za-z0-9_]+)(?::([^}]*))?\}` will be replaced with the environment variable's value (`os.getenv(match.group(1))`).
- If an environment variable is not found:
  - If a default value is provided (e.g., `${DATABASE_URL:sqlite:///data.db}`), the fallback will be used.
  - If no default is provided (e.g., `${API_KEY}`), a `ConfigurationError` exception will be raised detailing the missing key.
- This will apply to both scalar strings and elements in lists.

## 2. JSON Schema Export (`config/export_schema.py`)

**Mechanism:**
- Pydantic models automatically support JSON schema generation via `model_json_schema()`.
- We will create a small executable script `config/export_schema.py` that writes the schema for `TenantConfigFile` to `config/tenant_config.schema.json`.
- Developers can then reference this schema at the top of their `tenant_config.yaml` files (`# yaml-language-server: $schema=./tenant_config.schema.json`) for IDE autocompletion and robust CLI validation.

## 3. Validation and Testing (`tests/test_config_loader.py`)

- **Nested Dictionary Test:** Ensure `${VAR}` is properly interpolated multiple layers deep.
- **List Iteration Test:** Ensure interpolation works on lists of strings.
- **Fallback Test:** Verify `${MISSING_VAR:default_string}` correctly injects `default_string`.
- **Exception Test:** Assert `ValueError` or `ConfigurationError` is raised on `${MISSING_VAR}` without a fallback.

## 4. Scope Check and Ambiguity Review
- **Scope:** Is this focused enough for a single implementation plan? Yes, this phase strictly implements pre-processing (interpolation) and offline tooling (schema export), independent of hot-reloading or inheritance.
- **Ambiguity:** What happens if an interpolated value looks like an integer but the schema expects a string? Pydantic's coercion handles this naturally, so returning the string value from the environment variable is safe.

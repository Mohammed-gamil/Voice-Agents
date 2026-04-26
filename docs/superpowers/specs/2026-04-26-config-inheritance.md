# Phase 2: Recursive Configuration Inheritance & Control

**Date:** 2026-04-26
**Topic:** Configurability Enhancements

## Overview
This document specifies the second phase of enhancing the project's configuration system: Config Inheritance. This allows tenants to share common settings by extending other tenants, reducing redundancy and making management of multiple similar tenants easier.

## 1. Schema Updates (`config/schema.py`)
- Add `extends: str | None = None` to `TenantConfig`.
- This field is optional and points to the `tenant_id` of the parent configuration.

## 2. Recursive Inheritance Resolution (`core/config_loader.py`)

**Mechanism:**
- A new function `_resolve_inheritance(tenant_id, all_raw_tenants, defaults, seen_ids)` will be implemented.
- It will recursively fetch the parent config if `extends` is present.
- **Order of Precedence:** `Defaults` -> `Grandparent` -> `Parent` -> `Child`.
- **Cycle Detection:** The `seen_ids` set will track the inheritance chain; if a `tenant_id` is repeated, a `ConfigurationError` (circular dependency) will be raised.

## 3. Dynamic List Merging (`_deep_merge`)

**Current Behavior:** Lists in the child completely overwrite lists in the parent.
**New Behavior:**
- If the child value is a standard list: `field: [item1, item2]`, it **overwrites** the parent list.
- If the child value is a special marker object: `field: { "append": [item1, item2] }`, it **appends** the items to the parent list.
- The `_deep_merge` function will detect this marker, perform the concatenation, and return a clean flat list to the caller.
- This applies recursively to nested structures.

## 4. Validation and Testing (`tests/test_config_loader.py`)

- **Basic Inheritance:** Verify child inherits scalar values from parent.
- **Multi-level Inheritance:** Verify `tenant_c` inherits from `tenant_b` which inherits from `tenant_a`.
- **List Overwrite:** Verify `field: [c1]` replaces `[p1]`.
- **List Append:** Verify `field: { "append": [c1] }` results in `[p1, c1]`.
- **Circular Dependency:** Verify an error is raised if `a` extends `b` and `b` extends `a`.
- **Missing Parent:** Verify an error is raised if `extends` points to a non-existent tenant.

## 5. Scope Check and Ambiguity Review
- **Scope:** This phase focuses purely on inheritance logic and list merging markers.
- **Ambiguity:** If a parent doesn't have a list but the child uses `"append"`, it will be treated as an append to an empty list `[]`.

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

def test_expand_env_existing_var():
    os.environ["EXISTING_VAR"] = "real_val"
    result = _expand_env("value is ${EXISTING_VAR:default_val}")
    assert result == "value is real_val"


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

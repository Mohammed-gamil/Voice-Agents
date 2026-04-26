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

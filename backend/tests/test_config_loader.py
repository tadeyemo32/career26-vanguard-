"""Tests for config_loader: load_config and error paths."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from config_loader import load_config


def test_load_config_default_path():
    """Default config path is config.yaml in project root; returns dict when file exists."""
    try:
        cfg = load_config()
    except FileNotFoundError:
        pytest.skip("config.yaml not in project root")
    assert isinstance(cfg, dict)
    assert "db" in cfg or "pipeline" in cfg or cfg == {}


def test_load_config_custom_path():
    """Custom path loads that file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump({"db": {"path": "data/custom.db"}, "foo": 1}, f)
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.get("db", {}).get("path") == "data/custom.db"
        assert cfg.get("foo") == 1
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_missing_file_raises():
    """Missing config file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.yaml")


def test_load_config_empty_file_returns_empty_dict():
    """Empty or whitespace-only file returns {} (yaml.safe_load returns None -> or {})."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg == {}
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_invalid_yaml_raises():
    """Invalid YAML raises (e.g. yaml.YAMLError)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: [[[")
        path = f.name
    try:
        with pytest.raises(yaml.YAMLError):
            load_config(path)
    finally:
        Path(path).unlink(missing_ok=True)

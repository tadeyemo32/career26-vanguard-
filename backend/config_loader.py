"""Load config.yaml from project root."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parent


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = config_path or _ROOT / "config.yaml"
    with open(path) as f:
        return yaml.safe_load(f) or {}

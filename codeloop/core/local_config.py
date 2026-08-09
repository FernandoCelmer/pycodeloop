"""Local config module"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".codeloop" / "config.json"


def read() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def write(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        CONFIG_PATH.write_text(json.dumps(data, indent=2))


def get_section(name: str) -> dict:
    return read().get(name, {})


def set_section(name: str, value: dict) -> None:
    data = read()
    data[name] = value
    write(data)

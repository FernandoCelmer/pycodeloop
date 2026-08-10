"""User Settings"""

from __future__ import annotations

from pycodeloop.abc.settings import Settings
from pycodeloop.core.store.json_store import default_store

_SECTION = "settings"


class UserSettings:
    """Saved user-level defaults (provider, model, max_turns,
    max_history_turns, ...) in `~/.pycodeloop/config.json` under
    "settings", so future runs don't need an env var every time."""

    def __init__(self, store: Settings | None = None) -> None:
        self.store = store or default_store

    def get_settings(self) -> dict:
        return self.store.get_section(_SECTION)

    def set_setting(self, key: str, value) -> None:
        settings = self.get_settings()
        settings[key] = value

        self.store.set_section(_SECTION, settings)

    def clear_setting(self, key: str) -> None:
        settings = self.get_settings()
        settings.pop(key, None)

        self.store.set_section(_SECTION, settings)

"""User settings — persisted defaults in ~/.codeloop/config.json"""

from __future__ import annotations

from codeloop.core.local_config import get_section, set_section

_SECTION = "settings"


def get_settings() -> dict:
    """Return the saved user-level defaults (provider, model, max_turns,
    max_history_turns, ...) — empty dict if none were ever saved."""
    return get_section(_SECTION)


def set_setting(key: str, value) -> None:
    """Persist one default under `key`, e.g. set_setting("provider",
    "openai") so every future run defaults to it without an env var."""
    settings = get_settings()
    settings[key] = value

    set_section(_SECTION, settings)


def clear_setting(key: str) -> None:
    settings = get_settings()
    settings.pop(key, None)

    set_section(_SECTION, settings)

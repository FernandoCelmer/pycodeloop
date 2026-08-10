"""Settings"""

import os

from dotenv import load_dotenv

from pycodeloop.core.persistence.user_settings import UserSettings

load_dotenv()

_saved = UserSettings().get_settings()

_PROVIDER = (
    os.environ.get("PYCODELOOP_PROVIDER") or _saved.get("provider") or "anthropic"
)
_MODEL = os.environ.get("PYCODELOOP_MODEL") or _saved.get("model")

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-5",
    "openai": "gpt-5",
    "ollama": "llama3.1",
}

API_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


class Settings:
    """Settings CodeLoop.

    Resolution order for provider/model/max_turns: env var (PYCODELOOP_*)
    > saved default (~/.pycodeloop/config.json, see user_settings.py) >
    hardcoded fallback.
    """

    PROVIDER = _PROVIDER
    MODEL = _MODEL or DEFAULT_MODELS.get(_PROVIDER)
    API_KEY = os.environ.get(API_KEY_ENV.get(_PROVIDER, ""))

    MAX_TURNS = int(
        os.environ.get("PYCODELOOP_MAX_TURNS") or _saved.get("max_turns") or 25
    )

    ICON = ":robot:"
    STEP_ICON = ":gear:"
    ERROR_ALERT = f"{ICON} [bold red]Error:[/bold red]"
    INFO_ALERT = f"{ICON} [bold blue]Info:[/bold blue]"
    WARNING_ALERT = f"{ICON} [bold yellow]Warning:[/bold yellow]"
    QUESTION_ALERT = f"{ICON} [bold magenta]Question:[/bold magenta]"

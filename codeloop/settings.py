"""Settings"""

import os

from dotenv import load_dotenv

load_dotenv()

_PROVIDER = os.environ.get("CODELOOP_PROVIDER", "anthropic")
_MODEL = os.environ.get("CODELOOP_MODEL")

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
    """Settings CodeLoop"""

    PROVIDER = _PROVIDER
    MODEL = _MODEL or DEFAULT_MODELS.get(_PROVIDER)
    API_KEY = os.environ.get(API_KEY_ENV.get(_PROVIDER, ""))

    MAX_TURNS = int(os.environ.get("CODELOOP_MAX_TURNS", "25"))

    ICON = ":robot:"
    STEP_ICON = ":gear:"
    ERROR_ALERT = f"{ICON} [bold red]Error:[/bold red]"
    INFO_ALERT = f"{ICON} [bold blue]Info:[/bold blue]"
    WARNING_ALERT = f"{ICON} [bold yellow]Warning:[/bold yellow]"
    QUESTION_ALERT = f"{ICON} [bold magenta]Question:[/bold magenta]"

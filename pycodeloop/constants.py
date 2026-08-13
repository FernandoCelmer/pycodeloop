"""Constants"""

from __future__ import annotations

from pathlib import Path

ENV_PROVIDER = "PYCODELOOP_PROVIDER"
ENV_MODEL = "PYCODELOOP_MODEL"
ENV_MAX_TURNS = "PYCODELOOP_MAX_TURNS"

DEFAULT_MAX_TURNS = 25
DEFAULT_PROVIDER_TEMPLATE = str(
    Path(__file__).parent / "providers" / "templates" / "anthropic.json"
)

ICON = ":robot:"
STEP_ICON = ":gear:"
ERROR_ALERT = f"{ICON} [bold red]Error:[/bold red]"
INFO_ALERT = f"{ICON} [bold blue]Info:[/bold blue]"
WARNING_ALERT = f"{ICON} [bold yellow]Warning:[/bold yellow]"
QUESTION_ALERT = f"{ICON} [bold magenta]Question:[/bold magenta]"

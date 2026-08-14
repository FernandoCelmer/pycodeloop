"""Settings"""

import os

from dotenv import load_dotenv

from pycodeloop.constants import (
    DEFAULT_MAX_TURNS,
    DEFAULT_PROVIDER_TEMPLATE,
    ENV_MAX_TURNS,
    ENV_MODEL,
    ENV_PROVIDER,
    ERROR_ALERT,
    ICON,
    INFO_ALERT,
    QUESTION_ALERT,
    STEP_ICON,
    WARNING_ALERT,
)
from pycodeloop.store.user_settings import UserSettings

load_dotenv()

_saved = UserSettings().get_settings()

_PROVIDER = (
    os.environ.get(ENV_PROVIDER)
    or _saved.get("provider")
    or DEFAULT_PROVIDER_TEMPLATE
)
_MODEL = os.environ.get(ENV_MODEL) or _saved.get("model")


class Settings:
    """Settings CodeLoop.

    Resolution order for provider/model/max_turns: env var (PYCODELOOP_*)
    > saved default (~/.pycodeloop/config.json, see user_settings.py) >
    hardcoded fallback.

    `PROVIDER` always names a `GenericProvider` source — a JSON config
    path (the default), a dotted `'module.path:ClassName'`, or the bare
    string `"generic"` paired with an explicit `--url`/`url=` kwarg.
    """

    PROVIDER = _PROVIDER
    MODEL = _MODEL
    API_KEY = None

    MAX_TURNS = int(
        os.environ.get(ENV_MAX_TURNS)
        or _saved.get("max_turns")
        or DEFAULT_MAX_TURNS
    )

    ICON = ICON
    STEP_ICON = STEP_ICON
    ERROR_ALERT = ERROR_ALERT
    INFO_ALERT = INFO_ALERT
    WARNING_ALERT = WARNING_ALERT
    QUESTION_ALERT = QUESTION_ALERT

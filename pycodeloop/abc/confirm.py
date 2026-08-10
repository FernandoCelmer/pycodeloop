"""Confirm ABC"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Confirm(ABC):
    """
    Import:
        You can import the **Confirm** class with:

            from pycodeloop.abc.confirm import Confirm

    Gate a dangerous tool call behind a yes/no/redirect question. Pass
    an instance to `Agent(confirm=...)` — a plain
    `Callable[[str, str], bool | str]` still works too, `Confirm` just
    gives pluggable implementations (CLI, chat, Slack bot, ...) a shared
    interface instead of an ad-hoc function.
    """

    @abstractmethod
    def ask(self, name: str, preview: str) -> bool | str:
        """Ask whether to run tool `name`, given a human-readable
        `preview` of what it would do.

        Return `True` to run it, `False` to skip it, or any other
        non-empty string to skip it and feed that text back to the
        model as a redirect.
        """

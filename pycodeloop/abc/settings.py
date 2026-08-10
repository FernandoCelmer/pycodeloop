"""Settings ABC"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Settings(ABC):
    """
    Import:
        You can import the **Settings** class with:

            from pycodeloop.abc.settings import Settings

    Key-value section store behind everything persisted locally —
    settings, the saved-session index, named MCP servers, and usage
    all go through one of these instead of touching a file directly.
    """

    @abstractmethod
    def get_section(self, name: str) -> dict:
        """Return the stored dict for `name`, or `{}` if never written."""

    @abstractmethod
    def set_section(self, name: str, value: dict) -> None:
        """Overwrite the stored dict for `name`."""

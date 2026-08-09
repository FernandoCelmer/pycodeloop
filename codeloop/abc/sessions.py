"""Sessions ABC"""

from __future__ import annotations

from abc import ABC, abstractmethod

from codeloop.core.session import Session


class Sessions(ABC):
    """
    Import:
        You can import the **Sessions** class with:

            from codeloop.abc.sessions import Sessions

    Persist and retrieve a `Session` by key, so a conversation can
    resume across process restarts. Inject via `Config(storage=...)`;
    `CodeLoop.run(prompt, session_key=...)` loads before and saves
    after each call when a storage is configured.
    """

    @abstractmethod
    def post(self, key: str, session: Session) -> None:
        """Persist `session` under `key`, overwriting any prior value."""

    @abstractmethod
    def get(self, key: str) -> Session | None:
        """Return the session stored under `key`, or `None` if absent."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the session stored under `key`. No-op if absent."""

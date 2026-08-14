"""CodeLoop __init__ module."""

__version__ = "0.6.0"
__description__ = "🤖 CodeLoop drives an agent through your code."

from .core.agent import Agent
from .core.codeloop import CodeLoop
from .core.config import Config
from .core.session import Session

__all__ = ["Agent", "CodeLoop", "Config", "Session"]

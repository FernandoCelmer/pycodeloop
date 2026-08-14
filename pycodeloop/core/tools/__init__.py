"""Tools __init__ module."""

from pycodeloop.abc.tool import Tool, ToolResult

from .bash import BashTool
from .delegate import DelegateTool
from .env import EnvTool
from .filesystem import (
    DeleteFileTool,
    EditFileTool,
    ListDirTool,
    ReadFileTool,
    WriteFileTool,
)
from .git import GitCommitTool, GitDiffTool, GitLogTool, GitStatusTool
from .http_request import HttpRequestTool
from .search import GlobTool, GrepTool
from .todo import TodoTool
from .web import WebFetchTool

DEFAULT_TOOLS: list[Tool] = [
    ReadFileTool(),
    WriteFileTool(),
    EditFileTool(),
    DeleteFileTool(),
    ListDirTool(),
    GlobTool(),
    GrepTool(),
    BashTool(),
    WebFetchTool(),
    HttpRequestTool(),
    GitStatusTool(),
    GitDiffTool(),
    GitLogTool(),
    GitCommitTool(),
    EnvTool(),
    TodoTool(),
]

READ_ONLY_TOOLS: list[Tool] = [
    ReadFileTool(),
    ListDirTool(),
    GlobTool(),
    GrepTool(),
    WebFetchTool(),
    GitStatusTool(),
    GitDiffTool(),
    GitLogTool(),
]

__all__ = [
    "Tool",
    "ToolResult",
    "BashTool",
    "DelegateTool",
    "EnvTool",
    "ReadFileTool",
    "WriteFileTool",
    "EditFileTool",
    "DeleteFileTool",
    "ListDirTool",
    "GlobTool",
    "GrepTool",
    "GitStatusTool",
    "GitDiffTool",
    "GitLogTool",
    "GitCommitTool",
    "HttpRequestTool",
    "TodoTool",
    "WebFetchTool",
    "DEFAULT_TOOLS",
    "READ_ONLY_TOOLS",
]

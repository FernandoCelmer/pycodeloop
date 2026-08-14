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

_read_file = ReadFileTool()
_list_dir = ListDirTool()
_glob = GlobTool()
_grep = GrepTool()
_web_fetch = WebFetchTool()
_git_status = GitStatusTool()
_git_diff = GitDiffTool()
_git_log = GitLogTool()

DEFAULT_TOOLS: list[Tool] = [
    _read_file,
    WriteFileTool(),
    EditFileTool(),
    DeleteFileTool(),
    _list_dir,
    _glob,
    _grep,
    BashTool(),
    _web_fetch,
    HttpRequestTool(),
    _git_status,
    _git_diff,
    _git_log,
    GitCommitTool(),
    EnvTool(),
    TodoTool(),
]

READ_ONLY_TOOLS: list[Tool] = [
    _read_file,
    _list_dir,
    _glob,
    _grep,
    _web_fetch,
    _git_status,
    _git_diff,
    _git_log,
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

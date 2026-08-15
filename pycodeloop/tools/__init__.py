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
from .sql import SqlQueryTool, SqlSchemaTool
from .web import WebFetchTool


def build_tools(workspace: bool = True) -> tuple[list[Tool], list[Tool]]:
    """Fresh `(default_tools, read_only_tools)` for one `Config` — never
    shared across `Config`/`Agent` instances, so each one's `workspace`
    jail setting stays scoped to itself instead of racing through a
    process-wide global. Tools common to both lists (read_file, list_dir,
    glob, grep, web_fetch, the read-only git/sql tools) are still
    instantiated once per call and shared between the two returned
    lists, matching the previous single-instantiation behavior — just
    scoped per call instead of per process."""
    read_file = ReadFileTool(workspace=workspace)
    list_dir = ListDirTool(workspace=workspace)
    glob_tool = GlobTool(workspace=workspace)
    grep = GrepTool(workspace=workspace)
    web_fetch = WebFetchTool()
    git_status = GitStatusTool()
    git_diff = GitDiffTool()
    git_log = GitLogTool()
    sql_schema = SqlSchemaTool()
    sql_query = SqlQueryTool()

    default_tools: list[Tool] = [
        read_file,
        WriteFileTool(workspace=workspace),
        EditFileTool(workspace=workspace),
        DeleteFileTool(workspace=workspace),
        list_dir,
        glob_tool,
        grep,
        BashTool(),
        web_fetch,
        HttpRequestTool(),
        git_status,
        git_diff,
        git_log,
        GitCommitTool(),
        EnvTool(),
        sql_schema,
        sql_query,
    ]

    read_only_tools: list[Tool] = [
        read_file,
        list_dir,
        glob_tool,
        grep,
        web_fetch,
        git_status,
        git_diff,
        git_log,
        sql_schema,
        sql_query,
    ]

    return default_tools, read_only_tools


DEFAULT_TOOLS: list[Tool]
READ_ONLY_TOOLS: list[Tool]
DEFAULT_TOOLS, READ_ONLY_TOOLS = build_tools()

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
    "SqlSchemaTool",
    "SqlQueryTool",
    "WebFetchTool",
    "DEFAULT_TOOLS",
    "READ_ONLY_TOOLS",
    "build_tools",
]

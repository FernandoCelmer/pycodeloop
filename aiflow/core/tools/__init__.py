"""Tools __init__ module."""

from aiflow.abc.tool import Tool, ToolResult

from .bash import BashTool
from .filesystem import (
    DeleteFileTool,
    EditFileTool,
    ListDirTool,
    ReadFileTool,
    WriteFileTool,
)
from .search import GlobTool, GrepTool
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
]

__all__ = [
    "Tool",
    "ToolResult",
    "BashTool",
    "ReadFileTool",
    "WriteFileTool",
    "EditFileTool",
    "DeleteFileTool",
    "ListDirTool",
    "GlobTool",
    "GrepTool",
    "WebFetchTool",
    "DEFAULT_TOOLS",
]

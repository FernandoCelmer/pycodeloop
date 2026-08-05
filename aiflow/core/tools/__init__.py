"""Tools __init__ module."""

from aiflow.abc.tool import Tool, ToolResult

from .bash import BashTool
from .filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from .search import GrepTool

DEFAULT_TOOLS: list[Tool] = [
    ReadFileTool(),
    WriteFileTool(),
    EditFileTool(),
    ListDirTool(),
    GrepTool(),
    BashTool(),
]

__all__ = [
    "Tool",
    "ToolResult",
    "BashTool",
    "ReadFileTool",
    "WriteFileTool",
    "EditFileTool",
    "ListDirTool",
    "GrepTool",
    "DEFAULT_TOOLS",
]

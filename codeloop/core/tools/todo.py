"""Todo Tool"""

from __future__ import annotations

from codeloop.abc.tool import Tool, ToolResult

_ACTIONS = {"list", "add", "complete", "clear"}


class TodoTool(Tool):
    """Scratchpad checklist for multi-step tasks. State lives on the tool
    instance, so it persists for as long as this instance is reused across
    turns (the default — `Agent` builds each tool once per session)."""

    name = "todo"
    description = (
        "Track a checklist of steps for a multi-step task. Actions: "
        "'add' (needs `text`), 'complete' (needs `item_id`), 'list', "
        "'clear'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": sorted(_ACTIONS)},
            "text": {"type": "string"},
            "item_id": {"type": "integer"},
        },
        "required": ["action"],
    }

    def __init__(self) -> None:
        self._items: list[dict] = []
        self._next_id = 1

    def _render(self) -> str:
        if not self._items:
            return "(empty)"
        return "\n".join(
            f"[{'x' if item['done'] else ' '}] {item['id']}. {item['text']}"
            for item in self._items
        )

    def run(
        self,
        action: str,
        text: str = "",
        item_id: int | None = None,
    ) -> ToolResult:
        if action not in _ACTIONS:
            return ToolResult(output=f"Unknown action: {action}", is_error=True)

        if action == "add":
            if not text:
                return ToolResult(output="text is required", is_error=True)
            self._items.append({"id": self._next_id, "text": text, "done": False})
            self._next_id += 1
            return ToolResult(output=self._render())

        if action == "complete":
            item = next((i for i in self._items if i["id"] == item_id), None)
            if item is None:
                return ToolResult(output=f"No item with id {item_id}", is_error=True)
            item["done"] = True
            return ToolResult(output=self._render())

        if action == "clear":
            self._items.clear()
            self._next_id = 1
            return ToolResult(output="(empty)")

        return ToolResult(output=self._render())

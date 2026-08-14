"""Response-parsing strategies shared by `GenericProvider`: the default
OpenAI chat-completions shape, the Anthropic messages shape, and an
arbitrary shape driven by dot-path config."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pycodeloop.abc.provider import ProviderResponse, ToolCall, Usage


def default_openai_response(data: dict) -> ProviderResponse:
    choice = data["choices"][0]
    message = choice["message"]

    tool_calls = [
        ToolCall(
            id=call["id"],
            name=call["function"]["name"],
            arguments=json.loads(call["function"].get("arguments") or "{}"),
            extra={k: v for k, v in call.items() if k not in ("id", "type", "function")}
            or None,
        )
        for call in (message.get("tool_calls") or [])
    ]

    usage = data.get("usage") or {}
    return ProviderResponse(
        text=message.get("content") or "",
        tool_calls=tool_calls,
        stop_reason=choice.get("finish_reason") or "stop",
        usage=Usage(
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        ),
        raw=data,
    )


def anthropic_response(data: dict) -> ProviderResponse:
    text = ""
    tool_calls = []
    for block in data.get("content") or []:
        if block.get("type") == "text":
            text += block.get("text") or ""
        elif block.get("type") == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=block["id"],
                    name=block["name"],
                    arguments=block.get("input") or {},
                )
            )

    usage = data.get("usage") or {}
    return ProviderResponse(
        text=text,
        tool_calls=tool_calls,
        stop_reason=data.get("stop_reason") or "end_turn",
        usage=Usage(
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        ),
        raw=data,
    )


def get_path(data: Any, path: str, default: Any = None) -> Any:
    """Dot-path lookup, e.g. 'choices.0.message.content'."""
    current = data
    for part in path.split("."):
        if current is None:
            return default
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return default
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return default
    return current if current is not None else default


def response_parser_from_paths(
    paths: dict,
) -> Callable[[dict], ProviderResponse]:
    text_path = paths.get("text", "choices.0.message.content")
    tool_calls_path = paths.get("tool_calls", "choices.0.message.tool_calls")
    stop_reason_path = paths.get("stop_reason", "choices.0.finish_reason")
    input_tokens_path = paths.get("input_tokens", "usage.prompt_tokens")
    output_tokens_path = paths.get("output_tokens", "usage.completion_tokens")
    tool_call_id_path = paths.get("tool_call_id", "id")
    tool_call_name_path = paths.get("tool_call_name", "function.name")
    tool_call_arguments_path = paths.get("tool_call_arguments", "function.arguments")

    def parser(data: dict) -> ProviderResponse:
        raw_tool_calls = get_path(data, tool_calls_path, []) or []
        tool_calls = []
        for call in raw_tool_calls:
            arguments = get_path(call, tool_call_arguments_path, "{}")
            if isinstance(arguments, str):
                arguments = json.loads(arguments or "{}")
            tool_calls.append(
                ToolCall(
                    id=get_path(call, tool_call_id_path, ""),
                    name=get_path(call, tool_call_name_path, ""),
                    arguments=arguments or {},
                )
            )

        return ProviderResponse(
            text=get_path(data, text_path, "") or "",
            tool_calls=tool_calls,
            stop_reason=get_path(data, stop_reason_path, "stop") or "stop",
            usage=Usage(
                input_tokens=get_path(data, input_tokens_path, 0) or 0,
                output_tokens=get_path(data, output_tokens_path, 0) or 0,
            ),
            raw=data,
        )

    return parser

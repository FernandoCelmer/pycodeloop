"""Json Provider"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aiflow.abc.provider import ProviderResponse, ToolCall, Usage
from aiflow.providers.generic import GenericProvider


def _get_path(data: Any, path: str, default: Any = None) -> Any:
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


def _response_parser_from_paths(
    paths: dict,
) -> Callable[[dict], ProviderResponse]:
    text_path = paths.get("text", "choices.0.message.content")
    tool_calls_path = paths.get("tool_calls", "choices.0.message.tool_calls")
    stop_reason_path = paths.get("stop_reason", "choices.0.finish_reason")
    input_tokens_path = paths.get("input_tokens", "usage.prompt_tokens")
    output_tokens_path = paths.get("output_tokens", "usage.completion_tokens")
    tool_call_id_path = paths.get("tool_call_id", "id")
    tool_call_name_path = paths.get("tool_call_name", "function.name")
    tool_call_arguments_path = paths.get(
        "tool_call_arguments", "function.arguments"
    )

    def parser(data: dict) -> ProviderResponse:
        raw_tool_calls = _get_path(data, tool_calls_path, []) or []
        tool_calls = []
        for call in raw_tool_calls:
            arguments = _get_path(call, tool_call_arguments_path, "{}")
            if isinstance(arguments, str):
                arguments = json.loads(arguments or "{}")
            tool_calls.append(
                ToolCall(
                    id=_get_path(call, tool_call_id_path, ""),
                    name=_get_path(call, tool_call_name_path, ""),
                    arguments=arguments or {},
                )
            )

        return ProviderResponse(
            text=_get_path(data, text_path, "") or "",
            tool_calls=tool_calls,
            stop_reason=_get_path(data, stop_reason_path, "stop") or "stop",
            usage=Usage(
                input_tokens=_get_path(data, input_tokens_path, 0) or 0,
                output_tokens=_get_path(data, output_tokens_path, 0) or 0,
            ),
            raw=data,
        )

    return parser


def load_provider_from_json(path: str | Path) -> GenericProvider:
    """Build a `GenericProvider` from a JSON config file — no Python
    code needed for an HTTP LLM API close to the OpenAI chat-completions
    shape (request body always matches it; `response_paths` only needs
    setting for a different response shape).

    Example config:

        {
          "url": "https://api.example.com/v1/chat/completions",
          "model": "my-model",
          "api_key_env": "MY_API_KEY",
          "headers": {"X-Custom": "value"},
          "timeout": 60,
          "response_paths": {
            "text": "choices.0.message.content",
            "tool_calls": "choices.0.message.tool_calls",
            "stop_reason": "choices.0.finish_reason",
            "input_tokens": "usage.prompt_tokens",
            "output_tokens": "usage.completion_tokens",
            "tool_call_id": "id",
            "tool_call_name": "function.name",
            "tool_call_arguments": "function.arguments"
          }
        }

    `response_paths` is optional — omit it entirely for an API that
    already matches the OpenAI shape.
    """
    data = json.loads(Path(path).read_text())

    api_key = data.get("api_key")
    if not api_key and data.get("api_key_env"):
        api_key = os.environ.get(data["api_key_env"])

    response_parser = None
    if "response_paths" in data:
        response_parser = _response_parser_from_paths(data["response_paths"])

    return GenericProvider(
        url=data["url"],
        model=data.get("model", ""),
        api_key=api_key,
        headers=data.get("headers") or {},
        response_parser=response_parser,
        timeout=data.get("timeout", 60.0),
    )

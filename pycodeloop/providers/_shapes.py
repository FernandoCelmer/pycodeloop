"""Message/tool-schema shape builders shared by `GenericProvider` for the
two request formats it knows out of the box (OpenAI chat-completions,
Anthropic messages)."""

from __future__ import annotations

import json

from pycodeloop.core.session import Message


def openai_tool_schema(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get(
                    "parameters", {"type": "object", "properties": {}}
                ),
            },
        }
        for tool in tools
    ]


def to_openai_messages(system_prompt: str, messages: list[Message]) -> list[dict]:
    out: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        if msg.role == "user":
            if msg.images:
                content = [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image}"},
                    }
                    for image in msg.images
                ]
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                out.append({"role": "user", "content": content})
            else:
                out.append({"role": "user", "content": msg.content})
        elif msg.role == "assistant":
            if not msg.content and not msg.tool_calls:
                continue

            entry: dict = {
                "role": "assistant",
                "content": msg.content or None,
            }
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call["arguments"]),
                        },
                        **(call.get("extra") or {}),
                    }
                    for call in msg.tool_calls
                ]
            out.append(entry)
        elif msg.role == "tool":
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content or "",
                }
            )
    return out


def anthropic_tool_schema(tools: list[dict]) -> list[dict]:
    return [
        {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "input_schema": tool.get(
                "parameters", {"type": "object", "properties": {}}
            ),
        }
        for tool in tools
    ]


def to_anthropic_messages(messages: list[Message]) -> list[dict]:
    out: list[dict] = []
    for msg in messages:
        if msg.role == "user":
            if msg.images:
                content = [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image,
                        },
                    }
                    for image in msg.images
                ]
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                out.append({"role": "user", "content": content})
            else:
                out.append({"role": "user", "content": msg.content})
        elif msg.role == "assistant":
            if not msg.content and not msg.tool_calls:
                continue

            content = []
            if msg.content:
                content.append({"type": "text", "text": msg.content})
            for call in msg.tool_calls or []:
                content.append(
                    {
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["name"],
                        "input": call["arguments"],
                    }
                )
            out.append({"role": "assistant", "content": content})
        elif msg.role == "tool":
            out.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content or "",
                        }
                    ],
                }
            )
    return out

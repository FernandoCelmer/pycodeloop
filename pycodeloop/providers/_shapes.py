"""Message/tool-schema shape builders shared by `GenericProvider` for the
two request formats it knows out of the box (OpenAI chat-completions,
Anthropic messages)."""

from __future__ import annotations

import json
from collections.abc import Callable

from pycodeloop.core.session import Message

RequestBuilder = Callable[[str, "list[Message]", "list[dict]", str], dict]


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


def request_builder_from_config(request_cfg: dict) -> RequestBuilder:
    body_paths = request_cfg.get("body_paths", {})
    model_key = body_paths.get("model", "model")
    messages_key = body_paths.get("messages", "messages")
    tools_key = body_paths.get("tools", "tools")
    role_key = body_paths.get("message_role", "role")
    content_key = body_paths.get("message_content", "content")

    params = request_cfg.get("params") or {}
    params_key = request_cfg.get("params_key")
    extra_body = request_cfg.get("extra_body") or {}

    message_shape = request_cfg.get("message_shape", "openai")
    tool_schema = request_cfg.get("tool_schema", "openai")

    system_key = body_paths.get("system")
    if system_key is None and message_shape == "anthropic":
        system_key = "system"

    build_tools = (
        anthropic_tool_schema if tool_schema == "anthropic" else openai_tool_schema
    )

    def builder(
        system_prompt: str, messages: list, tools: list[dict], model: str
    ) -> dict:
        if message_shape == "anthropic":
            out_messages = to_anthropic_messages(messages)
        else:
            out_messages = to_openai_messages(system_prompt, messages)
            if system_key:
                out_messages = out_messages[1:]

            if role_key != "role" or content_key != "content":
                renamed = []
                for msg in out_messages:
                    new_msg = dict(msg)
                    if "role" in new_msg:
                        new_msg[role_key] = new_msg.pop("role")
                    if "content" in new_msg:
                        new_msg[content_key] = new_msg.pop("content")
                    renamed.append(new_msg)
                out_messages = renamed

        body: dict = {model_key: model, messages_key: out_messages}
        if system_key:
            body[system_key] = system_prompt
        if tools:
            body[tools_key] = build_tools(tools)

        if params_key:
            body[params_key] = params
        else:
            body.update(params)
        body.update(extra_body)
        return body

    return builder

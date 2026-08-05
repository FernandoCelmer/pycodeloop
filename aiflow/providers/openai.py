"""OpenAI (GPT) provider."""

from __future__ import annotations

import json
from collections.abc import Callable

from aiflow.abc.provider import Provider, ProviderResponse, ToolCall, Usage
from aiflow.core.session import Message


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, model: str = "gpt-5", api_key: str | None = None, **kwargs) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    @staticmethod
    def _tool_schema(tools: list[dict]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
                },
            }
            for tool in tools
        ]

    @staticmethod
    def _to_openai_messages(system_prompt: str, messages: list[Message]) -> list[dict]:
        out: list[dict] = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            if msg.role == "user":
                out.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                entry: dict = {"role": "assistant", "content": msg.content or None}
                if msg.tool_calls:
                    entry["tool_calls"] = [
                        {
                            "id": call["id"],
                            "type": "function",
                            "function": {
                                "name": call["name"],
                                "arguments": json.dumps(call["arguments"]),
                            },
                        }
                        for call in msg.tool_calls
                    ]
                out.append(entry)
            elif msg.role == "tool":
                out.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.tool_call_id,
                        "content": msg.content,
                    }
                )
        return out

    def complete(
        self,
        system_prompt: str,
        messages: list[Message],
        tools: list[dict],
        on_delta: Callable[[str], None] | None = None,
    ) -> ProviderResponse:
        kwargs = {
            "model": self.model,
            "messages": self._to_openai_messages(system_prompt, messages),
            "tools": self._tool_schema(tools) if tools else None,
        }

        if on_delta is None:
            response = self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            message = choice.message
            text = message.content or ""
            tool_calls = [
                ToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments=json.loads(call.function.arguments or "{}"),
                )
                for call in (message.tool_calls or [])
            ]
            stop_reason = choice.finish_reason or "stop"
            usage = Usage(
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
            )
            return ProviderResponse(
                text=text, tool_calls=tool_calls, stop_reason=stop_reason, usage=usage, raw=response
            )

        text = ""
        pending: dict[int, dict] = {}
        stop_reason = "stop"
        usage = Usage()
        stream = self.client.chat.completions.create(
            stream=True, stream_options={"include_usage": True}, **kwargs
        )
        for chunk in stream:
            if chunk.usage:
                usage = Usage(
                    input_tokens=chunk.usage.prompt_tokens,
                    output_tokens=chunk.usage.completion_tokens,
                )

            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            if delta.content:
                text += delta.content
                on_delta(delta.content)

            for tc in delta.tool_calls or []:
                acc = pending.setdefault(tc.index, {"id": None, "name": None, "arguments": ""})
                if tc.id:
                    acc["id"] = tc.id
                if tc.function and tc.function.name:
                    acc["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    acc["arguments"] += tc.function.arguments

            if choice.finish_reason:
                stop_reason = choice.finish_reason

        tool_calls = [
            ToolCall(id=acc["id"], name=acc["name"], arguments=json.loads(acc["arguments"] or "{}"))
            for acc in pending.values()
        ]
        return ProviderResponse(text=text, tool_calls=tool_calls, stop_reason=stop_reason, usage=usage, raw=None)

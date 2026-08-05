"""OpenAI (GPT) provider."""

from __future__ import annotations

import json

from aiflow.abc.provider import Provider, ProviderResponse, ToolCall
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

    def complete(self, system_prompt: str, messages: list[Message], tools: list[dict]) -> ProviderResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._to_openai_messages(system_prompt, messages),
            tools=self._tool_schema(tools) if tools else None,
        )

        choice = response.choices[0]
        message = choice.message
        tool_calls = [
            ToolCall(
                id=call.id,
                name=call.function.name,
                arguments=json.loads(call.function.arguments or "{}"),
            )
            for call in (message.tool_calls or [])
        ]

        return ProviderResponse(
            text=message.content or "",
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason or "stop",
            raw=response,
        )

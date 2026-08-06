"""Anthropic Provider"""

from __future__ import annotations

from collections.abc import Callable

from aiflow.abc.provider import Provider, ProviderResponse, ToolCall, Usage
from aiflow.core.session import Message


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(
        self,
        model: str = "claude-sonnet-5",
        api_key: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    @staticmethod
    def _tool_schema(tools: list[dict]) -> list[dict]:
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

    @staticmethod
    def _to_anthropic_messages(messages: list[Message]) -> list[dict]:
        out: list[dict] = []
        for msg in messages:
            if msg.role == "user":
                out.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
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
                                "content": msg.content,
                            }
                        ],
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
            "max_tokens": self.extra.get("max_tokens", 4096),
            "system": system_prompt,
            "messages": self._to_anthropic_messages(messages),
            "tools": self._tool_schema(tools) if tools else [],
        }

        if on_delta is None:
            response = self.client.messages.create(**kwargs)
        else:
            with self.client.messages.stream(**kwargs) as stream:
                for delta in stream.text_stream:
                    on_delta(delta)
                response = stream.get_final_message()

        text = ""
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id, name=block.name, arguments=block.input
                    )
                )

        usage = Usage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return ProviderResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "end_turn",
            usage=usage,
            raw=response,
        )

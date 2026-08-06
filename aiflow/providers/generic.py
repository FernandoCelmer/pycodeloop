"""Generic Provider"""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx

from aiflow.abc.provider import Provider, ProviderResponse, ToolCall, Usage
from aiflow.core.session import Message
from aiflow.providers.openai import OpenAIProvider

RequestBuilder = Callable[[str, "list[Message]", "list[dict]", str], dict]
ResponseParser = Callable[[dict], ProviderResponse]


def _default_request(
    system_prompt: str, messages: list[Message], tools: list[dict], model: str
) -> dict:
    return {
        "model": model,
        "messages": OpenAIProvider._to_openai_messages(
            system_prompt, messages
        ),
        "tools": OpenAIProvider._tool_schema(tools) if tools else None,
    }


def _default_response(data: dict) -> ProviderResponse:
    choice = data["choices"][0]
    message = choice["message"]

    tool_calls = [
        ToolCall(
            id=call["id"],
            name=call["function"]["name"],
            arguments=json.loads(call["function"].get("arguments") or "{}"),
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


class GenericProvider(Provider):
    """Any JSON chat-completions HTTP API via httpx, no vendor SDK.
    Defaults to the OpenAI request/response shape; override
    `request_builder`/`response_parser` for a different one."""

    name = "generic"

    def __init__(
        self,
        url: str,
        model: str,
        api_key: str | None = None,
        headers: dict[str, str] | None = None,
        request_builder: RequestBuilder | None = None,
        response_parser: ResponseParser | None = None,
        timeout: float = 60.0,
        **kwargs,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self.url = url
        self.headers = headers or {}
        self.request_builder = request_builder or _default_request
        self.response_parser = response_parser or _default_response
        self.timeout = timeout
        self._uses_default_parser = response_parser is None
        self.client = httpx.Client(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self.headers}
        if self.api_key and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def complete(
        self,
        system_prompt: str,
        messages: list[Message],
        tools: list[dict],
        on_delta: Callable[[str], None] | None = None,
    ) -> ProviderResponse:
        body = self.request_builder(system_prompt, messages, tools, self.model)

        if on_delta is not None and self._uses_default_parser:
            return self._stream(body, on_delta)

        response = self.client.post(
            self.url, json=body, headers=self._headers()
        )
        response.raise_for_status()
        result = self.response_parser(response.json())
        if on_delta is not None and result.text:
            on_delta(result.text)
        return result

    def _stream(
        self, body: dict, on_delta: Callable[[str], None]
    ) -> ProviderResponse:
        body = {**body, "stream": True}
        text = ""
        pending: dict[int, dict] = {}
        stop_reason = "stop"
        usage = Usage()

        with self.client.stream(
            "POST", self.url, json=body, headers=self._headers()
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                payload = line[len("data: ") :]
                if payload == "[DONE]":
                    break
                chunk = json.loads(payload)

                if chunk.get("usage"):
                    usage = Usage(
                        input_tokens=chunk["usage"].get("prompt_tokens", 0),
                        output_tokens=chunk["usage"].get(
                            "completion_tokens", 0
                        ),
                    )

                choices = chunk.get("choices") or []
                if not choices:
                    continue
                choice = choices[0]
                delta = choice.get("delta") or {}

                if delta.get("content"):
                    text += delta["content"]
                    on_delta(delta["content"])

                for tc in delta.get("tool_calls") or []:
                    index = tc.get("index", 0)
                    acc = pending.setdefault(
                        index, {"id": None, "name": None, "arguments": ""}
                    )
                    if tc.get("id"):
                        acc["id"] = tc["id"]
                    function = tc.get("function") or {}
                    if function.get("name"):
                        acc["name"] = function["name"]
                    if function.get("arguments"):
                        acc["arguments"] += function["arguments"]

                if choice.get("finish_reason"):
                    stop_reason = choice["finish_reason"]

        tool_calls = [
            ToolCall(
                id=acc["id"],
                name=acc["name"],
                arguments=json.loads(acc["arguments"] or "{}"),
            )
            for acc in pending.values()
        ]
        return ProviderResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage=usage,
            raw=None,
        )

"""Json Provider"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from pycodeloop.abc.provider import Provider, ProviderResponse, ToolCall, Usage
from pycodeloop.constants import ENV_API_KEY
from pycodeloop.core.session import Message
from pycodeloop.providers._responses import (
    anthropic_response,
    default_openai_response,
    response_parser_from_paths,
)
from pycodeloop.providers._shapes import (
    RequestBuilder,
    openai_tool_schema,
    request_builder_from_config,
    to_openai_messages,
)

ResponseParser = Callable[[dict], ProviderResponse]


class GenericProvider(Provider):
    """Any JSON chat-completions HTTP API via the stdlib, no vendor SDK.
    Defaults to the OpenAI request/response shape; override
    `request_builder`/`response_parser` for a different one, or build one
    declaratively from a config file with `GenericProvider.from_json`.

    Example config for `from_json`:

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
          },
          "request": {
            "body_paths": {
              "model": "model",
              "messages": "messages",
              "tools": "tools",
              "system": "system",
              "message_role": "role",
              "message_content": "content"
            },
            "params": {"temperature": 0.7, "max_tokens": 1024}
          }
        }

    `response_paths` is optional — omit it entirely for an API that
    already matches the OpenAI shape. `request` is optional too.
    `body_paths` renames/relocates the outgoing body's fields (set
    `system` to move the system prompt to its own top-level key
    instead of embedding it as the first message; `message_role`/
    `message_content` rename per-message keys). `params` are extra
    static fields merged into every request body (e.g. `temperature`,
    `max_tokens`, vendor-specific flags).
    """

    name = "generic"

    def __init__(
        self,
        url: str,
        model: str,
        api_key: str | None = None,
        headers: dict[str, str] | None = None,
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer ",
        request_builder: RequestBuilder | None = None,
        response_parser: ResponseParser | None = None,
        timeout: float = 60.0,
        **kwargs,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self.url = url
        self.headers = headers or {}
        self.auth_header = auth_header
        self.auth_prefix = auth_prefix
        self.request_builder = request_builder or self._default_request
        self.response_parser = response_parser or default_openai_response
        self.timeout = timeout
        self._uses_default_parser = response_parser is None
        self._config_path: Path | None = None

    @classmethod
    def from_json(cls, path: str | Path) -> GenericProvider:
        """Build a `GenericProvider` from a JSON config file — no Python
        code needed for an HTTP LLM API close to the OpenAI
        chat-completions shape."""
        provider = cls._build_from_json(path)
        provider._config_path = Path(path)
        return provider

    @classmethod
    def _build_from_json(cls, path: str | Path) -> GenericProvider:
        data = json.loads(Path(path).read_text())

        api_key = data.get("api_key")
        if not api_key:
            api_key = os.environ.get(ENV_API_KEY)
        if not api_key and data.get("api_key_env"):
            api_key = os.environ.get(data["api_key_env"])

        response_parser = None
        if data.get("response_shape") == "anthropic":
            response_parser = anthropic_response
        elif "response_paths" in data:
            response_parser = response_parser_from_paths(data["response_paths"])

        request_builder = None
        if "request" in data:
            request_builder = request_builder_from_config(data["request"])

        return cls(
            url=data["url"],
            model=data.get("model", ""),
            api_key=api_key,
            headers=data.get("headers") or {},
            auth_header=data.get("auth_header", "Authorization"),
            auth_prefix=data.get("auth_prefix", "Bearer "),
            request_builder=request_builder,
            response_parser=response_parser,
            timeout=data.get("timeout", 60.0),
        )

    def reload(self) -> None:
        """Re-read the JSON config this provider was built from and apply
        its `url`/`model`/`headers`/etc in place — lets a running session
        pick up edits to the file (e.g. a different `model`) without a
        restart. No-op if this provider wasn't built via `from_json`."""
        if self._config_path is None:
            return

        fresh = self._build_from_json(self._config_path)
        self.url = fresh.url
        self.model = fresh.model
        self.api_key = fresh.api_key
        self.headers = fresh.headers
        self.auth_header = fresh.auth_header
        self.auth_prefix = fresh.auth_prefix
        self.request_builder = fresh.request_builder
        self.response_parser = fresh.response_parser
        self.timeout = fresh.timeout
        self._uses_default_parser = fresh._uses_default_parser

    @staticmethod
    def _default_request(
        system_prompt: str,
        messages: list[Message],
        tools: list[dict],
        model: str,
    ) -> dict:
        return {
            "model": model,
            "messages": to_openai_messages(system_prompt, messages),
            "tools": openai_tool_schema(tools) if tools else None,
        }

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self.headers}
        if self.api_key and self.auth_header not in headers:
            headers[self.auth_header] = f"{self.auth_prefix}{self.api_key}"
        return headers

    def _open(self, body: dict):
        data = json.dumps(body).encode()
        request = urllib.request.Request(
            self.url, data=data, headers=self._headers(), method="POST"
        )
        try:
            return urllib.request.urlopen(request, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise urllib.error.HTTPError(
                exc.url, exc.code, f"{exc.reason}: {detail}", exc.headers, exc.fp
            ) from None

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

        with self._open(body) as response:
            raw = response.read()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            snippet = raw.decode(errors="replace")[:500]
            raise ValueError(
                f"{self.url} returned malformed/truncated JSON ({exc}): {snippet!r}"
            ) from None

        result = self.response_parser(data)

        if on_delta is not None and result.text:
            on_delta(result.text)

        return result

    def _stream(self, body: dict, on_delta: Callable[[str], None]) -> ProviderResponse:
        body = {**body, "stream": True}
        text = ""
        pending: dict[int, dict] = {}
        stop_reason = "stop"
        usage = Usage()

        with self._open(body) as response:
            for raw_line in response:
                line = raw_line.decode().strip()
                if not line or not line.startswith("data: "):
                    continue
                payload = line[len("data: ") :]
                if payload == "[DONE]":
                    break
                chunk = json.loads(payload)

                if chunk.get("usage"):
                    usage = Usage(
                        input_tokens=chunk["usage"].get("prompt_tokens", 0),
                        output_tokens=chunk["usage"].get("completion_tokens", 0),
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
                        index, {"id": None, "name": None, "arguments": "", "extra": {}}
                    )
                    if tc.get("id"):
                        acc["id"] = tc["id"]
                    function = tc.get("function") or {}
                    if function.get("name"):
                        acc["name"] = function["name"]
                    if function.get("arguments"):
                        acc["arguments"] += function["arguments"]
                    acc["extra"].update(
                        {k: v for k, v in tc.items() if k not in ("index", "id", "type", "function")}
                    )

                if choice.get("finish_reason"):
                    stop_reason = choice["finish_reason"]

        tool_calls = [
            ToolCall(
                id=acc["id"],
                name=acc["name"],
                arguments=json.loads(acc["arguments"] or "{}"),
                extra=acc["extra"] or None,
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

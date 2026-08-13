"""Command serve module — CodeLoop as a JSON-RPC-over-stdio server for
editor integrations (VSCode extension, etc). One JSON object per line
on stdout (notifications/responses) and stdin (requests); nothing else
may ever be written to stdout, or it corrupts the stream for the client."""

from __future__ import annotations

import json
import queue
import sys
import threading
import uuid

import typer

from pycodeloop.abc.provider import Usage
from pycodeloop.cli.flow import PROVIDER_HELP, _load_mcp_tools, resolve_provider
from pycodeloop.cli.render import console
from pycodeloop.core.codeloop import CodeLoop
from pycodeloop.core.config import Config


class RpcServer:
    """Wires `Agent` callbacks to JSON-RPC notifications instead of the
    interactive CLI's `console.print` calls, and turns the synchronous
    `confirm()` gate into a request/response round-trip over the wire."""

    def __init__(
        self,
        flow: CodeLoop,
        provider_name: str,
        model_name: str,
        auto_approve: bool = False,
    ) -> None:
        self.flow = flow
        self.provider_name = provider_name
        self.model_name = model_name
        self.auto_approve = auto_approve
        self._out_lock = threading.Lock()
        self._confirm_waiters: dict[str, queue.Queue] = {}
        self._cancel_event: threading.Event | None = None
        self._wire_callbacks()

    def _send(self, message: dict) -> None:
        line = json.dumps(message)
        with self._out_lock:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()

    def _notify(self, method: str, params: dict) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def _wire_callbacks(self) -> None:
        agent = self.flow.agent

        def on_text_delta(delta: str) -> None:
            self._notify("chat/textDelta", {"delta": delta})

        def on_tool_call(name: str, args: dict) -> None:
            self._notify("chat/toolCall", {"name": name, "arguments": args})

        def on_tool_result(name: str, result: str, is_error: bool) -> None:
            self._notify(
                "chat/toolResult",
                {"name": name, "result": result, "isError": is_error},
            )

        def on_usage(turn: Usage, total: Usage, elapsed: float) -> None:
            self._notify(
                "chat/usage",
                {
                    "turnInputTokens": turn.input_tokens,
                    "turnOutputTokens": turn.output_tokens,
                    "totalInputTokens": total.input_tokens,
                    "totalOutputTokens": total.output_tokens,
                    "elapsed": elapsed,
                },
            )

        def on_context(used_tokens: int, limit_tokens: int) -> None:
            self._notify("chat/context", {"used": used_tokens, "limit": limit_tokens})

        def on_retry(attempt: int, delay: float, exc: Exception) -> None:
            self._notify(
                "chat/retry",
                {"attempt": attempt, "delay": delay, "error": str(exc)},
            )

        def on_compact_start() -> None:
            self._notify("chat/compactStart", {})

        def on_compact_end(before: int, after: int) -> None:
            self._notify("chat/compactEnd", {"before": before, "after": after})

        def confirm(name: str, preview: str) -> bool | str:
            if self.auto_approve:
                self._notify("chat/autoApproved", {"name": name})
                return True

            request_id = str(uuid.uuid4())
            answer_queue: queue.Queue = queue.Queue()
            self._confirm_waiters[request_id] = answer_queue
            self._notify(
                "chat/confirmRequest",
                {"id": request_id, "name": name, "preview": preview},
            )
            try:
                return answer_queue.get()
            finally:
                self._confirm_waiters.pop(request_id, None)

        agent.on_text_delta = on_text_delta
        agent.on_tool_call = on_tool_call
        agent.on_tool_result = on_tool_result
        agent.on_usage = on_usage
        agent.on_context = on_context
        agent.on_retry = on_retry
        agent.on_compact_start = on_compact_start
        agent.on_compact_end = on_compact_end
        agent.confirm = confirm

    def _run_chat(self, request_id, params: dict) -> None:
        self._cancel_event = threading.Event()
        try:
            result = self.flow.run(
                params.get("prompt", ""),
                session_key=params.get("sessionKey"),
                images=params.get("images"),
                cancel_event=self._cancel_event,
            )
            self._send({"jsonrpc": "2.0", "id": request_id, "result": {"text": result}})
        except Exception as exc:
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32000, "message": str(exc)},
                }
            )

    def handle(self, request: dict) -> None:
        method = request.get("method")
        params = request.get("params") or {}
        request_id = request.get("id")

        if method == "chat/send":
            threading.Thread(
                target=self._run_chat, args=(request_id, params), daemon=True
            ).start()
        elif method == "chat/cancel":
            if self._cancel_event is not None:
                self._cancel_event.set()
        elif method == "chat/confirmResponse":
            waiter = self._confirm_waiters.get(params.get("id"))
            if waiter is not None:
                waiter.put(params.get("answer"))
        elif method == "session/list":
            storage = self.flow.config.storage
            sessions = (
                storage.list_sessions() if hasattr(storage, "list_sessions") else {}
            )
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "sessions": [
                            {"key": key, **meta} for key, meta in sessions.items()
                        ]
                    },
                }
            )
        elif method == "session/load":
            storage = self.flow.config.storage
            key = params.get("key")
            session = storage.get(key) if storage is not None and key else None
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "messages": [
                            {
                                "role": message.role,
                                "content": message.content,
                                "toolCallId": message.tool_call_id,
                                "toolCalls": message.tool_calls,
                                "images": message.images,
                            }
                            for message in (session.history() if session else [])
                        ]
                    },
                }
            )
        elif method == "initialize":
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "provider": self.provider_name,
                        "model": self.model_name,
                    },
                }
            )
        elif request_id is not None:
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Unknown method: {method}"},
                }
            )

    def serve_forever(self) -> None:
        self._notify(
            "ready", {"provider": self.provider_name, "model": self.model_name}
        )
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue
            self.handle(request)


def serve(
    provider: str = typer.Option(None, help=PROVIDER_HELP),
    model: str = typer.Option(None, help="Model name override."),
    base_url: str = typer.Option(
        None, help="Override the API endpoint (local/self-hosted servers)."
    ),
    url: str = typer.Option(
        None, help="Endpoint URL, required for --provider generic."
    ),
    mcp: list[str] = typer.Option(
        None, help="MCP server as 'command arg1 arg2'; repeatable."
    ),
    skills: bool = typer.Option(
        True,
        "--skills/--no-skills",
        help="Discover Claude/Cursor/AGENTS.md skills and expose a read_skill tool.",
    ),
    skills_refresh: bool = typer.Option(
        False, "--skills-refresh", help="Bypass the skills cache and rescan."
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Auto-approve dangerous tool calls instead of round-tripping a confirmRequest.",
    ),
) -> None:
    """Run CodeLoop as a JSON-RPC-over-stdio server for editor
    integrations — no interactive terminal output, one JSON message
    per line on stdin/stdout."""
    console.file = sys.stderr

    provider_instance, provider_name = resolve_provider(provider, model, base_url, url)
    config = Config(
        provider=provider_instance,
        tools=_load_mcp_tools(mcp),
        skills=skills,
        skills_refresh=skills_refresh,
    )
    flow = CodeLoop(config=config)
    RpcServer(
        flow, provider_name, provider_instance.model, auto_approve=yes
    ).serve_forever()

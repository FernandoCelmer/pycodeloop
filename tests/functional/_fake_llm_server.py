"""A real local HTTP server speaking the OpenAI chat-completions shape,
used by functional tests to drive `GenericProvider`/`Agent`/`CodeLoop`
through an actual socket instead of mocking `urlopen`."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class FakeLLMServer:
    """Serves scripted chat-completions responses in order, one per
    POST request, and records the decoded request bodies it received."""

    def __init__(self, responses: list[dict]) -> None:
        self.responses = list(responses)
        self.requests: list[dict] = []
        self._call_index = 0
        self._lock = threading.Lock()

        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - stdlib method name
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")

                with server._lock:
                    server.requests.append(body)
                    index = server._call_index
                    server._call_index += 1

                response = server.responses[index]

                if body.get("stream"):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.end_headers()
                    for chunk in _to_sse_chunks(response):
                        self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                    self.wfile.write(b"data: [DONE]\n\n")
                else:
                    payload = json.dumps(response).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)

            def log_message(self, *args) -> None:
                pass

        self._httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        host, port = self._httpd.server_address
        return f"http://{host}:{port}/v1/chat/completions"

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=2)


def chat_completion(
    text: str = "",
    tool_calls: list[dict] | None = None,
    finish_reason: str = "stop",
) -> dict:
    message: dict = {"role": "assistant", "content": text}
    if tool_calls:
        message["tool_calls"] = tool_calls
        finish_reason = "tool_calls"

    return {
        "choices": [{"message": message, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }


def _to_sse_chunks(response: dict) -> list[dict]:
    """Collapse a scripted non-streaming chat-completion response into
    the single-chunk SSE stream `GenericProvider._stream()` expects."""
    choice = response["choices"][0]
    message = choice["message"]

    return [
        {
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": message.get("content") or None,
                        "tool_calls": [
                            {
                                "index": i,
                                "id": tc["id"],
                                "function": tc["function"],
                            }
                            for i, tc in enumerate(message.get("tool_calls") or [])
                        ]
                        or None,
                    },
                    "finish_reason": choice.get("finish_reason"),
                }
            ],
            "usage": response.get("usage"),
        }
    ]


def tool_call(call_id: str, name: str, arguments: dict) -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }

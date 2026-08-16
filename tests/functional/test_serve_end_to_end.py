"""Functional: `pycodeloop serve` as a real subprocess, driven over its
actual stdin/stdout JSON-RPC pipe — no in-process shortcuts, this is
exactly how the VSCode extension talks to it."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from tests.functional._fake_llm_server import (
    FakeLLMServer,
    chat_completion,
    tool_call,
)

_TIMEOUT = 10.0


class ServeSubprocess:
    def __init__(
        self, url: str, cwd: Path, extra_args: list[str] | None = None
    ) -> None:
        # Config() defaults storage/trace to real files under
        # ~/.pycodeloop/ when neither is overridden — this is a real
        # subprocess, so redirect HOME instead of mock.patch.
        self._home_tmpdir = tempfile.TemporaryDirectory()
        env = {**os.environ, "HOME": self._home_tmpdir.name}
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "pycodeloop.cli.main",
                "serve",
                "--provider",
                "generic",
                "--model",
                "test-model",
                "--url",
                url,
                "--no-skills",
                *(extra_args or []),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=cwd,
            env=env,
        )
        self._lines: queue.Queue = queue.Queue()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self) -> None:
        for line in self.process.stdout:
            line = line.strip()
            if line:
                self._lines.put(json.loads(line))

    def send(self, message: dict) -> None:
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def next_message(self, timeout: float = _TIMEOUT) -> dict:
        return self._lines.get(timeout=timeout)

    def close(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
        self._home_tmpdir.cleanup()


class TestServeEndToEnd(unittest.TestCase):
    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.tmp_path = Path(tmpdir.name).resolve()

        self.server: FakeLLMServer | None = None
        self.client: ServeSubprocess | None = None
        self.addCleanup(self._teardown)

    def _teardown(self) -> None:
        if self.client is not None:
            self.client.close()
        if self.server is not None:
            self.server.close()

    def test_ready_notification_reports_provider_and_model(self):
        self.server = FakeLLMServer([chat_completion(text="hi")])
        self.client = ServeSubprocess(self.server.url, self.tmp_path)

        ready = self.client.next_message()

        self.assertEqual(ready["method"], "ready")
        self.assertEqual(ready["params"]["provider"], "generic")
        self.assertEqual(ready["params"]["model"], "test-model")

    def test_chat_send_streams_tool_call_and_returns_final_text(self):
        self.server = FakeLLMServer(
            [
                chat_completion(
                    tool_calls=[tool_call("call-1", "list_dir", {"path": "."})]
                ),
                chat_completion(text="Here's the directory listing."),
            ]
        )
        self.client = ServeSubprocess(self.server.url, self.tmp_path)
        self.client.next_message()  # ready

        self.client.send(
            {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "chat/send",
                "params": {"prompt": "list files"},
            }
        )

        methods = []
        response = None
        while response is None:
            message = self.client.next_message()
            if message.get("id") == "1" and "result" in message:
                response = message
            else:
                methods.append(message.get("method"))

        self.assertIn("chat/toolCall", methods)
        self.assertIn("chat/toolResult", methods)
        self.assertEqual(
            response["result"]["text"], "Here's the directory listing."
        )

    def test_chat_send_emits_on_request_notification(self):
        self.server = FakeLLMServer([chat_completion(text="hi")])
        self.client = ServeSubprocess(self.server.url, self.tmp_path)
        self.client.next_message()  # ready

        self.client.send(
            {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "chat/send",
                "params": {"prompt": "hello"},
            }
        )

        messages = []
        response = None
        while response is None:
            message = self.client.next_message()
            if message.get("id") == "1" and "result" in message:
                response = message
            else:
                messages.append(message)

        request_notification = next(
            m for m in messages if m.get("method") == "chat/request"
        )
        self.assertIsInstance(
            request_notification["params"]["messageCount"], int
        )
        self.assertIsInstance(request_notification["params"]["toolCount"], int)

    def test_dangerous_tool_blocks_on_confirm_round_trip(self):
        self.server = FakeLLMServer(
            [
                chat_completion(
                    tool_calls=[
                        tool_call(
                            "call-1",
                            "write_file",
                            {"path": "note.txt", "content": "hi"},
                        )
                    ]
                ),
                chat_completion(text="Wrote it."),
            ]
        )
        self.client = ServeSubprocess(self.server.url, self.tmp_path)
        self.client.next_message()  # ready

        self.client.send(
            {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "chat/send",
                "params": {"prompt": "write a note"},
            }
        )

        confirm_request = None
        while confirm_request is None:
            message = self.client.next_message()
            if message.get("method") == "chat/confirmRequest":
                confirm_request = message

        self.assertEqual(confirm_request["params"]["name"], "write_file")

        self.client.send(
            {
                "jsonrpc": "2.0",
                "method": "chat/confirmResponse",
                "params": {
                    "id": confirm_request["params"]["id"],
                    "answer": True,
                },
            }
        )

        response = None
        while response is None:
            message = self.client.next_message()
            if message.get("id") == "1" and "result" in message:
                response = message

        self.assertEqual(response["result"]["text"], "Wrote it.")
        self.assertEqual((self.tmp_path / "note.txt").read_text(), "hi")

    def test_yes_flag_auto_approves_without_confirm_round_trip(self):
        self.server = FakeLLMServer(
            [
                chat_completion(
                    tool_calls=[
                        tool_call(
                            "call-1",
                            "write_file",
                            {"path": "note.txt", "content": "hi"},
                        )
                    ]
                ),
                chat_completion(text="Wrote it."),
            ]
        )
        self.client = ServeSubprocess(
            self.server.url, self.tmp_path, extra_args=["--yes"]
        )
        self.client.next_message()  # ready

        self.client.send(
            {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "chat/send",
                "params": {"prompt": "write a note"},
            }
        )

        notifications = []
        response = None
        while response is None:
            message = self.client.next_message()
            if message.get("id") == "1" and "result" in message:
                response = message
            else:
                notifications.append(message)

        methods = [n.get("method") for n in notifications]
        self.assertIn("chat/autoApproved", methods)
        self.assertNotIn("chat/confirmRequest", methods)
        self.assertEqual(response["result"]["text"], "Wrote it.")
        self.assertEqual((self.tmp_path / "note.txt").read_text(), "hi")

        auto_approved = next(
            n for n in notifications if n.get("method") == "chat/autoApproved"
        )
        self.assertIn("note.txt", auto_approved["params"]["preview"])


if __name__ == "__main__":
    unittest.main()

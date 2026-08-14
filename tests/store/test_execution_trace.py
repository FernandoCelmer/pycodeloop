"""Test JsonlTracer"""

import json
import tempfile
import unittest
from pathlib import Path

from pycodeloop.store.execution_trace import JsonlTracer


class TestJsonlTracer(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.directory = Path(self._tmpdir.name) / "logs"

    def test_appends_one_json_line_per_event(self):
        tracer = JsonlTracer("s1", directory=self.directory)

        tracer({"type": "run_start", "prompt_len": 5})
        tracer({"type": "turn", "stop_reason": "stop"})

        lines = tracer.path.read_text().splitlines()
        self.assertEqual(len(lines), 2)

        first = json.loads(lines[0])
        self.assertEqual(first["type"], "run_start")
        self.assertEqual(first["prompt_len"], 5)
        self.assertIn("ts", first)

        second = json.loads(lines[1])
        self.assertEqual(second["type"], "turn")

    def test_writes_to_session_scoped_file(self):
        tracer = JsonlTracer("my-session", directory=self.directory)

        self.assertEqual(tracer.path, self.directory / "my-session.jsonl")

    def test_creates_the_log_directory_if_missing(self):
        nested = self.directory / "nested"
        JsonlTracer("s1", directory=nested)

        self.assertTrue(nested.is_dir())


if __name__ == "__main__":
    unittest.main()

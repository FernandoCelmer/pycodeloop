"""Test JsonlTracer"""

import json
import tempfile
import threading
import unittest
from pathlib import Path

from pycodeloop.store.execution_trace import JsonlTracer


class TestJsonlTracer(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.directory = (Path(self._tmpdir.name) / "logs").resolve()

    def test_appends_one_json_line_per_event(self):
        tracer = JsonlTracer("s1", directory=self.directory)
        self.addCleanup(tracer.close)

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
        self.addCleanup(tracer.close)

        self.assertEqual(tracer.path, self.directory / "my-session.jsonl")

    def test_creates_the_log_directory_if_missing(self):
        nested = self.directory / "nested"
        tracer = JsonlTracer("s1", directory=nested)
        self.addCleanup(tracer.close)

        self.assertTrue(nested.is_dir())

    def test_rejects_a_session_key_that_escapes_the_log_directory(self):
        with self.assertRaises(ValueError):
            JsonlTracer("../../etc/cron.d/evil", directory=self.directory)

    def test_rejects_a_session_key_with_a_path_separator(self):
        with self.assertRaises(ValueError):
            JsonlTracer("nested/evil", directory=self.directory)

    def test_close_lets_the_file_be_reopened_cleanly(self):
        tracer = JsonlTracer("s1", directory=self.directory)
        tracer({"type": "run_start"})
        tracer.close()

        self.assertEqual(len(tracer.path.read_text().splitlines()), 1)

    def test_concurrent_writes_never_interleave_mid_line(self):
        tracer = JsonlTracer("s1", directory=self.directory)
        self.addCleanup(tracer.close)

        def write_many(worker: int) -> None:
            for i in range(50):
                tracer({"type": "turn", "worker": worker, "i": i})

        threads = [
            threading.Thread(target=write_many, args=(worker,))
            for worker in range(8)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        lines = tracer.path.read_text().splitlines()
        self.assertEqual(len(lines), 400)
        for line in lines:
            json.loads(line)


if __name__ == "__main__":
    unittest.main()

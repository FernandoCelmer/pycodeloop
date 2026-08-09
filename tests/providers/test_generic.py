"""Test load_provider_from_json"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx

from aiflow.providers import get_provider
from aiflow.providers.generic import GenericProvider
from aiflow.providers.json_provider import load_provider_from_json


class JsonProviderTestCase(unittest.TestCase):
    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.tmp_path = Path(tmpdir.name)

    def _write_config(self, config: dict) -> Path:
        path = self.tmp_path / "provider.json"
        path.write_text(json.dumps(config))
        return path


class TestLoadProviderFromJson(JsonProviderTestCase):
    def test_builds_generic_provider_from_config(self):
        path = self._write_config(
            {
                "url": "http://fake/v1/chat/completions",
                "model": "my-model",
                "api_key": "sk-test",
                "headers": {"X-Custom": "1"},
            }
        )

        provider = load_provider_from_json(path)

        self.assertIsInstance(provider, GenericProvider)
        self.assertEqual(provider.url, "http://fake/v1/chat/completions")
        self.assertEqual(provider.model, "my-model")
        self.assertEqual(provider.api_key, "sk-test")
        self.assertEqual(provider.headers, {"X-Custom": "1"})

    def test_reads_api_key_from_env_var(self):
        path = self._write_config(
            {
                "url": "http://fake/v1/chat/completions",
                "model": "my-model",
                "api_key_env": "MY_FAKE_KEY",
            }
        )

        with mock.patch.dict("os.environ", {"MY_FAKE_KEY": "from-env"}):
            provider = load_provider_from_json(path)

        self.assertEqual(provider.api_key, "from-env")

    def test_default_response_shape_without_response_paths(self):
        path = self._write_config(
            {"url": "http://fake/v1/chat/completions", "model": "my-model"}
        )
        provider = load_provider_from_json(path)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "hi"}, "finish_reason": "stop"}
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                },
            )

        provider.client = httpx.Client(transport=httpx.MockTransport(handler))
        result = provider.complete("sys", [], [])

        self.assertEqual(result.text, "hi")

    def test_custom_response_paths(self):
        path = self._write_config(
            {
                "url": "http://fake/answer",
                "model": "my-model",
                "response_paths": {
                    "text": "result.answer",
                    "input_tokens": "meta.tokens_in",
                    "output_tokens": "meta.tokens_out",
                },
            }
        )
        provider = load_provider_from_json(path)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "result": {"answer": "custom shape works"},
                    "meta": {"tokens_in": 7, "tokens_out": 4},
                },
            )

        provider.client = httpx.Client(transport=httpx.MockTransport(handler))
        result = provider.complete("sys", [], [])

        self.assertEqual(result.text, "custom shape works")
        self.assertEqual(result.usage.input_tokens, 7)
        self.assertEqual(result.usage.output_tokens, 4)

    def test_custom_tool_call_paths(self):
        path = self._write_config(
            {
                "url": "http://fake/answer",
                "model": "my-model",
                "response_paths": {
                    "text": "text",
                    "tool_calls": "actions",
                    "tool_call_id": "call_id",
                    "tool_call_name": "fn",
                    "tool_call_arguments": "args",
                },
            }
        )
        provider = load_provider_from_json(path)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "text": "",
                    "actions": [
                        {
                            "call_id": "1",
                            "fn": "read_file",
                            "args": '{"path": "a.py"}',
                        }
                    ],
                },
            )

        provider.client = httpx.Client(transport=httpx.MockTransport(handler))
        result = provider.complete("sys", [], [])

        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0].name, "read_file")
        self.assertEqual(result.tool_calls[0].arguments, {"path": "a.py"})


class TestGetProviderJsonDispatch(JsonProviderTestCase):
    def test_get_provider_loads_json_config_by_path(self):
        path = self._write_config(
            {"url": "http://fake/v1/chat/completions", "model": "my-model"}
        )

        provider = get_provider(str(path))

        self.assertIsInstance(provider, GenericProvider)
        self.assertEqual(provider.model, "my-model")

    def test_get_provider_model_kwarg_overrides_json_config(self):
        path = self._write_config(
            {"url": "http://fake/v1/chat/completions", "model": "from-json"}
        )

        provider = get_provider(str(path), model="from-cli")

        self.assertEqual(provider.model, "from-cli")


if __name__ == "__main__":
    unittest.main()

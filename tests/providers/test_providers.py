"""Test provider registry and dotted-path loading"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pycodeloop.abc.provider import Provider, ProviderResponse
from pycodeloop.providers import GenericProvider, get_provider


class TestGetProvider(unittest.TestCase):
    def test_generic_requires_url(self):
        provider = get_provider("generic", model="llama3.1", url="http://x/chat")

        self.assertIsInstance(provider, GenericProvider)
        self.assertEqual(provider.url, "http://x/chat")

    def test_generic_reads_pycodeloop_api_key_env(self):
        with mock.patch.dict("os.environ", {"PYCODELOOP_API_KEY": "from-extension"}):
            provider = get_provider("generic", model="llama3.1", url="http://x/chat")

        self.assertEqual(provider.api_key, "from-extension")

    def test_rejects_unknown_name(self):
        with self.assertRaises(ValueError):
            get_provider("does-not-exist")

    def test_loads_json_config(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        config_path = Path(tmpdir.name) / "config.json"
        config_path.write_text(
            json.dumps({"url": "http://x/chat", "model": "my-model"})
        )

        provider = get_provider(str(config_path))

        self.assertIsInstance(provider, GenericProvider)
        self.assertEqual(provider.model, "my-model")

    def test_loads_custom_dotted_path(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)

        module_path = tmp_path / "my_custom_provider.py"
        module_path.write_text(
            "from pycodeloop.abc.provider import Provider, ProviderResponse\n"
            "\n"
            "class MyProvider(Provider):\n"
            "    def complete(\n"
            "        self, system_prompt, messages, tools, on_delta=None\n"
            "    ):\n"
            "        return ProviderResponse(\n"
            "            text='hi from custom provider'\n"
            "        )\n"
        )

        sys.path.insert(0, str(tmp_path))
        self.addCleanup(sys.path.remove, str(tmp_path))
        sys.modules.pop("my_custom_provider", None)
        self.addCleanup(sys.modules.pop, "my_custom_provider", None)

        provider = get_provider("my_custom_provider:MyProvider", model="local-model")

        self.assertIsInstance(provider, Provider)
        result = provider.complete("sys", [], [])
        self.assertIsInstance(result, ProviderResponse)
        self.assertEqual(result.text, "hi from custom provider")


if __name__ == "__main__":
    unittest.main()

"""Test provider registry and dotted-path loading"""

import sys
import tempfile
import unittest
from pathlib import Path

from codeloop.abc.provider import Provider, ProviderResponse
from codeloop.providers import OllamaProvider, get_provider


class TestOllamaProvider(unittest.TestCase):
    def test_defaults(self):
        provider = OllamaProvider()

        self.assertEqual(provider.model, "llama3.1")
        self.assertEqual(provider.base_url, "http://localhost:11434/v1")
        self.assertEqual(provider.api_key, "ollama")


class TestGetProvider(unittest.TestCase):
    def test_by_registry_name(self):
        provider = get_provider("ollama", model="llama3.1")

        self.assertIsInstance(provider, OllamaProvider)

    def test_rejects_unknown_name(self):
        with self.assertRaises(ValueError):
            get_provider("does-not-exist")

    def test_loads_custom_dotted_path(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        tmp_path = Path(tmpdir.name)

        module_path = tmp_path / "my_custom_provider.py"
        module_path.write_text(
            "from codeloop.abc.provider import Provider, ProviderResponse\n"
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

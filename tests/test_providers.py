import sys

import pytest

from aiflow.abc.provider import Provider, ProviderResponse
from aiflow.providers import OllamaProvider, get_provider


def test_ollama_provider_defaults():
    provider = OllamaProvider()

    assert provider.model == "llama3.1"
    assert provider.base_url == "http://localhost:11434/v1"
    assert provider.api_key == "ollama"


def test_get_provider_by_registry_name():
    provider = get_provider("ollama", model="llama3.1")

    assert isinstance(provider, OllamaProvider)


def test_get_provider_rejects_unknown_name():
    with pytest.raises(ValueError):
        get_provider("does-not-exist")


def test_get_provider_loads_custom_dotted_path(tmp_path, monkeypatch):
    module_path = tmp_path / "my_custom_provider.py"
    module_path.write_text(
        "from aiflow.abc.provider import Provider, ProviderResponse\n"
        "\n"
        "class MyProvider(Provider):\n"
        "    def complete(self, system_prompt, messages, tools, on_delta=None):\n"
        "        return ProviderResponse(text='hi from custom provider')\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("my_custom_provider", None)

    provider = get_provider("my_custom_provider:MyProvider", model="local-model")

    assert isinstance(provider, Provider)
    result = provider.complete("sys", [], [])
    assert isinstance(result, ProviderResponse)
    assert result.text == "hi from custom provider"

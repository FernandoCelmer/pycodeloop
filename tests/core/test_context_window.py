"""Test context_window_for"""

import unittest

from pycodeloop.core.context_window import (
    DEFAULT_CONTEXT_WINDOW,
    context_window_for,
)


class TestContextWindowFor(unittest.TestCase):
    def test_matches_every_templates_default_model(self):
        expected = {
            "claude-sonnet-5": 200_000,
            "gpt-5.6": 400_000,
            "gemini-3.6-flash": 1_000_000,
            "grok-4.5": 256_000,
            "openai/gpt-oss-120b": 128_000,
            "openai.gpt-oss-120b": 128_000,
            "kimi-k3": 256_000,
            "deepseek-v4-pro": 128_000,
            "meta/llama-3.3-70b-instruct": 128_000,
            "qwen-max": 128_000,
            "llama3.1": 128_000,
        }
        for model, size in expected.items():
            with self.subTest(model=model):
                self.assertEqual(context_window_for(model), size)

    def test_matching_is_case_insensitive(self):
        self.assertEqual(
            context_window_for("meta-llama/Llama-3.3-70B-Instruct-Turbo"),
            128_000,
        )

    def test_unknown_model_falls_back_to_the_conservative_default(self):
        self.assertEqual(
            context_window_for("some-future-vendor-model"),
            DEFAULT_CONTEXT_WINDOW,
        )
        self.assertEqual(DEFAULT_CONTEXT_WINDOW, 32_000)


if __name__ == "__main__":
    unittest.main()

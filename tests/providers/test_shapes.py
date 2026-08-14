"""Test the OpenAI/Anthropic message-shape builders used by GenericProvider"""

import unittest

from pycodeloop.core.session import Message
from pycodeloop.providers._shapes import (
    anthropic_tool_schema,
    request_builder_from_config,
    to_anthropic_messages,
    to_openai_messages,
)


class TestAnthropicMessageBuilding(unittest.TestCase):
    def test_plain_text_user_message_stays_a_string(self):
        out = to_anthropic_messages([Message(role="user", content="hi")])

        self.assertEqual(out, [{"role": "user", "content": "hi"}])

    def test_user_message_with_images_becomes_content_blocks(self):
        out = to_anthropic_messages(
            [Message(role="user", content="what is this?", images=["b64data"])]
        )

        self.assertEqual(
            out,
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "b64data",
                            },
                        },
                        {"type": "text", "text": "what is this?"},
                    ],
                }
            ],
        )

    def test_image_only_message_omits_empty_text_block(self):
        out = to_anthropic_messages(
            [Message(role="user", content="", images=["b64data"])]
        )

        self.assertEqual(len(out[0]["content"]), 1)
        self.assertEqual(out[0]["content"][0]["type"], "image")


class TestOpenAIMessageBuilding(unittest.TestCase):
    def test_plain_text_user_message_stays_a_string(self):
        out = to_openai_messages("sys", [Message(role="user", content="hi")])

        self.assertEqual(out[-1], {"role": "user", "content": "hi"})

    def test_user_message_with_images_becomes_content_blocks(self):
        out = to_openai_messages(
            "sys",
            [
                Message(
                    role="user", content="what is this?", images=["b64data"]
                )
            ],
        )

        self.assertEqual(
            out[-1],
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64,b64data"},
                    },
                    {"type": "text", "text": "what is this?"},
                ],
            },
        )

    def test_tool_call_extra_fields_round_trip_back_to_the_wire(self):
        """A ToolCall's vendor-specific `extra` (e.g. Gemini's
        extra_content.google.thought_signature) must be re-emitted as a
        sibling of id/type/function, unchanged, on the next request."""
        out = to_openai_messages(
            "sys",
            [
                Message(
                    role="assistant",
                    content="",
                    tool_calls=[
                        {
                            "id": "call_1",
                            "name": "read_file",
                            "arguments": {"path": "a.py"},
                            "extra": {
                                "extra_content": {
                                    "google": {"thought_signature": "abc123"}
                                }
                            },
                        }
                    ],
                )
            ],
        )

        self.assertEqual(
            out[-1]["tool_calls"][0]["extra_content"],
            {"google": {"thought_signature": "abc123"}},
        )


class TestAnthropicToolSchemaCaching(unittest.TestCase):
    def test_no_cache_control_by_default(self):
        schema = anthropic_tool_schema([{"name": "read_file"}])

        self.assertNotIn("cache_control", schema[-1])

    def test_marks_only_the_last_tool_as_cached(self):
        schema = anthropic_tool_schema(
            [{"name": "read_file"}, {"name": "write_file"}], cache=True
        )

        self.assertNotIn("cache_control", schema[0])
        self.assertEqual(schema[-1]["cache_control"], {"type": "ephemeral"})

    def test_empty_tool_list_stays_empty(self):
        self.assertEqual(anthropic_tool_schema([], cache=True), [])


class TestPromptCacheRequestBuilder(unittest.TestCase):
    def _cfg(self, prompt_cache: bool) -> dict:
        return {
            "message_shape": "anthropic",
            "tool_schema": "anthropic",
            "prompt_cache": prompt_cache,
        }

    def test_system_prompt_becomes_a_cached_content_block(self):
        builder = request_builder_from_config(self._cfg(True))

        body = builder("You are helpful.", [], [], "claude-x")

        self.assertEqual(
            body["system"],
            [
                {
                    "type": "text",
                    "text": "You are helpful.",
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        )

    def test_tools_get_a_cache_control_breakpoint_on_the_last_one(self):
        builder = request_builder_from_config(self._cfg(True))

        body = builder(
            "sys",
            [],
            [{"name": "read_file"}, {"name": "write_file"}],
            "claude-x",
        )

        self.assertEqual(
            body["tools"][-1]["cache_control"], {"type": "ephemeral"}
        )
        self.assertNotIn("cache_control", body["tools"][0])

    def test_disabled_by_default_system_stays_a_plain_string(self):
        builder = request_builder_from_config(self._cfg(False))

        body = builder("sys", [], [], "claude-x")

        self.assertEqual(body["system"], "sys")

    def test_only_applies_to_the_anthropic_tool_schema(self):
        cfg = {
            "message_shape": "openai",
            "tool_schema": "openai",
            "prompt_cache": True,
        }
        builder = request_builder_from_config(cfg)

        body = builder("sys", [], [{"name": "read_file"}], "gpt-x")

        self.assertNotIn("cache_control", body["tools"][0]["function"])


if __name__ == "__main__":
    unittest.main()

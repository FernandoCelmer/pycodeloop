"""Test AnthropicProvider._to_anthropic_messages()"""

import unittest

from pycodeloop.core.session import Message
from pycodeloop.providers.anthropic import AnthropicProvider


class TestAnthropicMessageBuilding(unittest.TestCase):
    def test_plain_text_user_message_stays_a_string(self):
        out = AnthropicProvider._to_anthropic_messages(
            [Message(role="user", content="hi")]
        )

        self.assertEqual(out, [{"role": "user", "content": "hi"}])

    def test_user_message_with_images_becomes_content_blocks(self):
        out = AnthropicProvider._to_anthropic_messages(
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
        out = AnthropicProvider._to_anthropic_messages(
            [Message(role="user", content="", images=["b64data"])]
        )

        self.assertEqual(len(out[0]["content"]), 1)
        self.assertEqual(out[0]["content"][0]["type"], "image")


if __name__ == "__main__":
    unittest.main()

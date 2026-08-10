"""Test OpenAIProvider._to_openai_messages()"""

import unittest

from pycodeloop.core.session import Message
from pycodeloop.providers.openai import OpenAIProvider


class TestOpenAIMessageBuilding(unittest.TestCase):
    def test_plain_text_user_message_stays_a_string(self):
        out = OpenAIProvider._to_openai_messages(
            "sys", [Message(role="user", content="hi")]
        )

        self.assertEqual(out[-1], {"role": "user", "content": "hi"})

    def test_user_message_with_images_becomes_content_blocks(self):
        out = OpenAIProvider._to_openai_messages(
            "sys",
            [Message(role="user", content="what is this?", images=["b64data"])],
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


if __name__ == "__main__":
    unittest.main()

"""Test GenericProvider class"""

import json
import unittest

import httpx

from aiflow.providers.generic import GenericProvider


class TestGenericProvider(unittest.TestCase):
    def test_complete_sends_openai_shaped_request(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            seen["auth"] = request.headers.get("authorization")
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "oi"}, "finish_reason": "stop"}
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 2},
                },
            )

        provider = GenericProvider(
            url="http://fake/v1/chat/completions",
            model="my-model",
            api_key="k",
        )
        provider.client = httpx.Client(transport=httpx.MockTransport(handler))

        result = provider.complete("sys", [], [])

        self.assertEqual(result.text, "oi")
        self.assertEqual(result.usage.input_tokens, 5)
        self.assertEqual(result.usage.output_tokens, 2)
        self.assertEqual(result.stop_reason, "stop")
        self.assertEqual(seen["body"]["model"], "my-model")
        self.assertEqual(seen["auth"], "Bearer k")

    def test_complete_raises_on_http_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        provider = GenericProvider(
            url="http://fake/v1/chat/completions", model="my-model"
        )
        provider.client = httpx.Client(transport=httpx.MockTransport(handler))

        with self.assertRaises(httpx.HTTPStatusError):
            provider.complete("sys", [], [])

    def test_streams_openai_sse_chunks(self):
        def handler(request: httpx.Request) -> httpx.Response:
            chunks = [
                'data: {"choices":[{"delta":{"content":"ol"}}]}\n\n',
                'data: {"choices":[{"delta":{"content":"a"},'
                '"finish_reason":"stop"}],"usage":{"prompt_tokens":3,'
                '"completion_tokens":1}}\n\n',
                "data: [DONE]\n\n",
            ]
            return httpx.Response(200, content="".join(chunks).encode())

        provider = GenericProvider(
            url="http://fake/v1/chat/completions", model="my-model"
        )
        provider.client = httpx.Client(transport=httpx.MockTransport(handler))

        deltas = []
        result = provider.complete("sys", [], [], on_delta=deltas.append)

        self.assertEqual(deltas, ["ol", "a"])
        self.assertEqual(result.text, "ola")
        self.assertEqual(result.stop_reason, "stop")
        self.assertEqual(result.usage.input_tokens, 3)
        self.assertEqual(result.usage.output_tokens, 1)

    def test_custom_response_parser_skips_streaming(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"answer": "hi"})

        from aiflow.abc.provider import ProviderResponse

        def parse(data):
            return ProviderResponse(text=data["answer"])

        provider = GenericProvider(
            url="http://fake/answer",
            model="my-model",
            response_parser=parse,
        )
        provider.client = httpx.Client(transport=httpx.MockTransport(handler))

        deltas = []
        result = provider.complete("sys", [], [], on_delta=deltas.append)

        self.assertEqual(result.text, "hi")
        self.assertEqual(deltas, ["hi"])


if __name__ == "__main__":
    unittest.main()

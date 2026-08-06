"""Test WebFetchTool class"""

import unittest
from unittest import mock

import httpx

from aiflow.core.tools.web import WebFetchTool


class TestWebFetchTool(unittest.TestCase):
    def test_fetches_plain_text(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                text="hello world",
                headers={"content-type": "text/plain"},
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with mock.patch(
            "httpx.get", side_effect=lambda url, **_kw: client.get(url)
        ):
            result = WebFetchTool().run(url="http://fake/text")

        self.assertEqual(result.output, "hello world")
        self.assertFalse(result.is_error)

    def test_strips_html_tags(self):
        html = (
            "<html><body><script>ignored()</script>"
            "<h1>Title</h1><p>Body text</p></body></html>"
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, text=html, headers={"content-type": "text/html"}
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with mock.patch(
            "httpx.get", side_effect=lambda url, **_kw: client.get(url)
        ):
            result = WebFetchTool().run(url="http://fake/page")

        self.assertIn("Title", result.output)
        self.assertIn("Body text", result.output)
        self.assertNotIn("ignored()", result.output)

    def test_reports_http_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text="not found")

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with mock.patch(
            "httpx.get", side_effect=lambda url, **_kw: client.get(url)
        ):
            result = WebFetchTool().run(url="http://fake/missing")

        self.assertTrue(result.is_error)


if __name__ == "__main__":
    unittest.main()

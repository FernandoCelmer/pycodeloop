"""Test WebFetchTool class"""

import unittest
from unittest import mock

import httpx

from pycodeloop.tools.web import WebFetchTool


def _fake_public_dns(hostname, *_args, **_kwargs):
    return [(None, None, None, None, ("93.184.216.34", 0))]


class TestWebFetchTool(unittest.TestCase):
    def test_fetches_plain_text(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                text="hello world",
                headers={"content-type": "text/plain"},
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with (
            mock.patch(
                "httpx.request",
                side_effect=lambda method, url, **_kw: client.request(
                    method, url
                ),
            ),
            mock.patch(
                "pycodeloop.tools._net.socket.getaddrinfo",
                side_effect=_fake_public_dns,
            ),
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
        with (
            mock.patch(
                "httpx.request",
                side_effect=lambda method, url, **_kw: client.request(
                    method, url
                ),
            ),
            mock.patch(
                "pycodeloop.tools._net.socket.getaddrinfo",
                side_effect=_fake_public_dns,
            ),
        ):
            result = WebFetchTool().run(url="http://fake/page")

        self.assertIn("Title", result.output)
        self.assertIn("Body text", result.output)
        self.assertNotIn("ignored()", result.output)

    def test_reports_http_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text="not found")

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with (
            mock.patch(
                "httpx.request",
                side_effect=lambda method, url, **_kw: client.request(
                    method, url
                ),
            ),
            mock.patch(
                "pycodeloop.tools._net.socket.getaddrinfo",
                side_effect=_fake_public_dns,
            ),
        ):
            result = WebFetchTool().run(url="http://fake/missing")

        self.assertTrue(result.is_error)

    def test_refuses_private_address(self):
        result = WebFetchTool().run(url="http://169.254.169.254/latest")

        self.assertTrue(result.is_error)
        self.assertIn("not a public address", result.output)

    def test_refuses_localhost(self):
        result = WebFetchTool().run(url="http://localhost:8080/admin")

        self.assertTrue(result.is_error)
        self.assertIn("not a public address", result.output)

    def test_does_not_follow_redirects(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                302, headers={"location": "http://internal/secret"}
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with (
            mock.patch(
                "httpx.request",
                side_effect=lambda method, url, **_kw: client.request(
                    method, url
                ),
            ),
            mock.patch(
                "pycodeloop.tools._net.socket.getaddrinfo",
                side_effect=_fake_public_dns,
            ),
        ):
            result = WebFetchTool().run(url="http://fake/redirect")

        self.assertTrue(result.is_error)
        self.assertIn("redirects to", result.output)


if __name__ == "__main__":
    unittest.main()

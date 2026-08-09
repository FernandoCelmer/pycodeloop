"""Test HttpRequestTool"""

import unittest
from unittest import mock

import httpx

from aiflow.core.tools.http_request import HttpRequestTool


def _fake_public_dns(hostname, *_args, **_kwargs):
    return [(None, None, None, None, ("93.184.216.34", 0))]


class TestHttpRequestTool(unittest.TestCase):
    def test_get_json(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": True})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with (
            mock.patch(
                "httpx.request",
                side_effect=lambda method, url, **kw: client.request(method, url),
            ),
            mock.patch(
                "aiflow.core.tools._net.socket.getaddrinfo",
                side_effect=_fake_public_dns,
            ),
        ):
            result = HttpRequestTool().run(url="http://fake/api")

        self.assertFalse(result.is_error)
        self.assertIn("ok", result.output)

    def test_reports_http_error_status(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with (
            mock.patch(
                "httpx.request",
                side_effect=lambda method, url, **kw: client.request(method, url),
            ),
            mock.patch(
                "aiflow.core.tools._net.socket.getaddrinfo",
                side_effect=_fake_public_dns,
            ),
        ):
            result = HttpRequestTool().run(url="http://fake/api")

        self.assertTrue(result.is_error)

    def test_refuses_private_address(self):
        result = HttpRequestTool().run(url="http://169.254.169.254/latest")

        self.assertTrue(result.is_error)
        self.assertIn("not a public address", result.output)

    def test_rejects_unsupported_method(self):
        result = HttpRequestTool().run(url="http://fake/api", method="TRACE")

        self.assertTrue(result.is_error)


if __name__ == "__main__":
    unittest.main()

"""Test _net module"""

import unittest
from unittest import mock

import httpx

from pycodeloop.tools._net import (
    BlockedHostError,
    is_blocked_host,
    resolve_safe_ip,
    safe_request,
)


def _fake_dns(addr):
    def fake(hostname, *_args, **_kwargs):
        return [(None, None, None, None, (addr, 0))]

    return fake


class TestResolveSafeIp(unittest.TestCase):
    def test_returns_the_address_for_a_public_host(self):
        with mock.patch(
            "pycodeloop.tools._net.socket.getaddrinfo",
            side_effect=_fake_dns("93.184.216.34"),
        ):
            self.assertEqual(resolve_safe_ip("example.com"), "93.184.216.34")

    def test_returns_none_for_a_private_address(self):
        with mock.patch(
            "pycodeloop.tools._net.socket.getaddrinfo",
            side_effect=_fake_dns("169.254.169.254"),
        ):
            self.assertIsNone(resolve_safe_ip("metadata.internal"))

    def test_returns_none_when_resolution_fails(self):
        import socket

        with mock.patch(
            "pycodeloop.tools._net.socket.getaddrinfo",
            side_effect=socket.gaierror,
        ):
            self.assertIsNone(resolve_safe_ip("does-not-resolve.invalid"))


class TestIsBlockedHost(unittest.TestCase):
    def test_public_host_is_not_blocked(self):
        with mock.patch(
            "pycodeloop.tools._net.socket.getaddrinfo",
            side_effect=_fake_dns("93.184.216.34"),
        ):
            self.assertFalse(is_blocked_host("example.com"))

    def test_private_host_is_blocked(self):
        with mock.patch(
            "pycodeloop.tools._net.socket.getaddrinfo",
            side_effect=_fake_dns("10.0.0.5"),
        ):
            self.assertTrue(is_blocked_host("internal"))


class TestSafeRequest(unittest.TestCase):
    def test_connects_to_the_resolved_ip_not_the_hostname(self):
        """Closes the DNS-rebinding gap: the request must go to the address
        resolved right before connecting, not a second, possibly different
        lookup made downstream — so it pins the URL host to that address."""
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["host"] = request.url.host
            captured["header"] = request.headers.get("host")
            captured["sni"] = request.extensions.get("sni_hostname")
            return httpx.Response(200)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with (
            mock.patch(
                "httpx.request",
                side_effect=lambda method, url, **kw: client.request(
                    method, url, **kw
                ),
            ),
            mock.patch(
                "pycodeloop.tools._net.socket.getaddrinfo",
                side_effect=_fake_dns("93.184.216.34"),
            ),
        ):
            safe_request("GET", "http://example.com/path")

        self.assertEqual(captured["host"], "93.184.216.34")
        self.assertEqual(captured["header"], "example.com")
        self.assertEqual(captured["sni"], "example.com")

    def test_raises_for_a_private_address(self):
        with (
            mock.patch(
                "pycodeloop.tools._net.socket.getaddrinfo",
                side_effect=_fake_dns("127.0.0.1"),
            ),
            self.assertRaises(BlockedHostError),
        ):
            safe_request("GET", "http://internal/path")


if __name__ == "__main__":
    unittest.main()

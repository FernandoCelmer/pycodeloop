"""Shared network-safety helpers for tools that make outbound HTTP calls."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse, urlunparse

import httpx


class BlockedHostError(Exception):
    pass


def _is_blocked_ip(addr: str) -> bool:
    ip = ipaddress.ip_address(addr)
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved


def resolve_safe_ip(hostname: str) -> str | None:
    """Resolve `hostname` to one address to connect to, or `None` if
    resolution fails or any resolved address is private/loopback/
    link-local/reserved — blocks SSRF against internal services and cloud
    metadata endpoints (e.g. 169.254.169.254)."""
    try:
        addrs = {info[4][0] for info in socket.getaddrinfo(hostname, None)}
    except socket.gaierror:
        return None
    if not addrs or any(_is_blocked_ip(addr) for addr in addrs):
        return None
    return next(iter(addrs))


def is_blocked_host(hostname: str) -> bool:
    return resolve_safe_ip(hostname) is None


def safe_request(method: str, url: str, **kwargs) -> httpx.Response:
    """SSRF-safe `httpx.request`: resolves `url`'s host once and connects
    directly to that pinned address instead of the hostname, so a second,
    attacker-controlled DNS answer (rebinding) between the safety check
    and the actual connection can't hand the request to a private/internal
    address. The original hostname is still sent via the `Host` header and
    TLS SNI, so routing and certificate validation work as normal."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise BlockedHostError(hostname or "")

    ip = resolve_safe_ip(hostname)
    if ip is None:
        raise BlockedHostError(hostname)

    netloc = ip if parsed.port is None else f"{ip}:{parsed.port}"
    pinned_url = urlunparse(parsed._replace(netloc=netloc))

    headers = dict(kwargs.pop("headers", None) or {})
    headers.setdefault("Host", hostname)

    extensions = dict(kwargs.pop("extensions", None) or {})
    extensions.setdefault("sni_hostname", hostname)

    return httpx.request(method, pinned_url, headers=headers, extensions=extensions, **kwargs)

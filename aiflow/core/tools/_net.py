"""Shared network-safety helpers for tools that make outbound HTTP calls."""

from __future__ import annotations

import ipaddress
import socket


def is_blocked_host(hostname: str) -> bool:
    """True if `hostname` resolves to a private/loopback/link-local address
    — blocks SSRF against internal services and cloud metadata endpoints
    (e.g. 169.254.169.254) via direct IPs or DNS rebinding."""
    try:
        addrs = {info[4][0] for info in socket.getaddrinfo(hostname, None)}
    except socket.gaierror:
        return True
    return any(
        ipaddress.ip_address(addr).is_private
        or ipaddress.ip_address(addr).is_loopback
        or ipaddress.ip_address(addr).is_link_local
        or ipaddress.ip_address(addr).is_reserved
        for addr in addrs
    )

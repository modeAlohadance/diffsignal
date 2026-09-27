from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeUrlError(ValueError):
    pass


def validate_url_syntax(url: str) -> tuple[str, int]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError("only http and https URLs are allowed")
    if not parsed.hostname:
        raise UnsafeUrlError("URL must include a hostname")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("credentials in URLs are not allowed")
    if parsed.hostname.rstrip(".").lower() == "localhost":
        raise UnsafeUrlError("local addresses are not allowed")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as error:
        raise UnsafeUrlError("invalid port") from error
    return parsed.hostname, port


def _resolve(hostname: str, port: int) -> set[str]:
    return {item[4][0] for item in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)}


async def ensure_public_url(url: str) -> None:
    hostname, port = validate_url_syntax(url)
    try:
        addresses = await asyncio.to_thread(_resolve, hostname, port)
    except socket.gaierror as error:
        raise UnsafeUrlError("hostname could not be resolved") from error
    if not addresses:
        raise UnsafeUrlError("hostname did not resolve to an address")
    for raw_address in addresses:
        address = ipaddress.ip_address(raw_address)
        if not address.is_global:
            raise UnsafeUrlError("private, loopback, link-local, and reserved addresses are blocked")

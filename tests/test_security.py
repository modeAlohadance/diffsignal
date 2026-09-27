import socket

import pytest

from diffsignal.security import UnsafeUrlError, ensure_public_url, validate_url_syntax


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://localhost/admin", "http://user:pass@example.com"])
def test_unsafe_url_syntax_is_rejected(url):
    with pytest.raises(UnsafeUrlError):
        validate_url_syntax(url)


@pytest.mark.asyncio
async def test_private_resolved_address_is_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("127.0.0.1", 80))])
    with pytest.raises(UnsafeUrlError):
        await ensure_public_url("http://example.test")


@pytest.mark.asyncio
async def test_public_resolved_address_is_allowed(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))])
    await ensure_public_url("https://example.test")

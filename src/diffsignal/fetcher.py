from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from .config import settings
from .security import ensure_public_url


ALLOWED_CONTENT_TYPES = ("text/", "application/json", "application/xml", "application/xhtml+xml")


class FetchError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FetchResult:
    url: str
    body: str | None
    content_type: str
    etag: str | None
    last_modified: str | None
    not_modified: bool = False


async def fetch_url(
    url: str,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> FetchResult:
    headers = {"User-Agent": "DiffSignal/0.1 (+https://github.com/modeAlohadance/diffsignal)"}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    owns_client = client is None
    active_client = client or httpx.AsyncClient(timeout=15.0, follow_redirects=False)
    current_url = url
    try:
        for _ in range(6):
            await ensure_public_url(current_url)
            async with active_client.stream("GET", current_url, headers=headers) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise FetchError("redirect response did not include a location")
                    current_url = urljoin(current_url, location)
                    continue
                if response.status_code == 304:
                    return FetchResult(current_url, None, "", etag, last_modified, True)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if not any(content_type.startswith(prefix) for prefix in ALLOWED_CONTENT_TYPES):
                    raise FetchError(f"unsupported content type: {content_type or 'unknown'}")
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > settings.max_response_bytes:
                        raise FetchError("response exceeded the configured size limit")
                encoding = response.encoding or "utf-8"
                body = bytes(data).decode(encoding, errors="replace")
                return FetchResult(
                    current_url,
                    body,
                    content_type,
                    response.headers.get("etag"),
                    response.headers.get("last-modified"),
                )
        raise FetchError("too many redirects")
    finally:
        if owns_client:
            await active_client.aclose()

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup
from soupsieve import SelectorSyntaxError


class InvalidSelectorError(ValueError):
    pass


def _clean_lines(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def normalize_content(body: str, content_type: str, ignore_selector: str | None = None) -> str:
    if "json" in content_type.lower():
        try:
            value = json.loads(body)
        except json.JSONDecodeError:
            return _clean_lines(body)
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)

    if "html" not in content_type.lower():
        return _clean_lines(body)

    soup = BeautifulSoup(body, "html.parser")
    for element in soup.select("script, style, noscript, template, svg"):
        element.decompose()
    if ignore_selector:
        try:
            ignored = soup.select(ignore_selector)
        except SelectorSyntaxError as error:
            raise InvalidSelectorError(f"invalid CSS selector: {ignore_selector}") from error
        for element in ignored:
            element.decompose()
    return _clean_lines(soup.get_text("\n"))

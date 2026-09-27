import pytest

from diffsignal.content import InvalidSelectorError, normalize_content


def test_html_normalization_removes_noise_and_ignored_elements():
    html = "<html><script>secret()</script><main>Hello   world</main><div class='clock'>12:00</div></html>"
    assert normalize_content(html, "text/html", ".clock") == "Hello world"


def test_json_normalization_is_order_independent():
    first = normalize_content('{"b": 2, "a": 1}', "application/json")
    second = normalize_content('{"a": 1, "b": 2}', "application/json")
    assert first == second


def test_invalid_selector_is_reported():
    with pytest.raises(InvalidSelectorError):
        normalize_content("<p>Hello</p>", "text/html", "[")

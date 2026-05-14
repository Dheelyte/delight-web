"""HTML sanitiser + reading-time helper.

The TipTap-era `render_doc` tests are gone; CKEditor produces HTML directly
and the server only needs to sanitise. We keep this file's name for now to
avoid churn in CI logs.
"""

from __future__ import annotations

from app.core.sanitize import clean_html
from app.services.posts import _reading_minutes


def test_sanitizer_strips_disallowed_tags() -> None:
    raw = '<p>ok <iframe src="x"></iframe> <script>bad()</script></p>'
    cleaned = clean_html(raw)
    assert "<iframe" not in cleaned
    assert "<script" not in cleaned
    assert "ok" in cleaned


def test_sanitizer_blocks_javascript_urls() -> None:
    raw = '<a href="javascript:alert(1)">x</a>'
    cleaned = clean_html(raw)
    assert "javascript:" not in cleaned


def test_sanitizer_keeps_safe_attrs() -> None:
    raw = '<a href="https://example.com" target="_blank">x</a>'
    cleaned = clean_html(raw)
    assert 'href="https://example.com"' in cleaned


def test_sanitizer_keeps_code_class_for_highlighting() -> None:
    raw = '<pre><code class="language-python">print(1)</code></pre>'
    cleaned = clean_html(raw)
    assert 'class="language-python"' in cleaned


def test_reading_minutes_floors_at_one() -> None:
    assert _reading_minutes("") == 1
    assert _reading_minutes("<p>only a couple words</p>") == 1


def test_reading_minutes_for_long_text() -> None:
    words = " ".join(["lorem"] * 880)
    html = f"<p>{words}</p>"
    assert _reading_minutes(html) == 4

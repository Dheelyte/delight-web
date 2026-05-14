"""Server-side HTML sanitisation for post bodies.

CKEditor 5 produces HTML directly; the server runs that HTML through nh3
with an explicit allowlist before persisting. The allowlist is the authority -
anything the editor emits that isn't listed here is dropped.

Note the inline-emphasis tags: CKEditor 5's Italic feature outputs `<i>`
(not `<em>`), and PasteFromOffice can emit `<b>` - both must be allowed or
formatting silently disappears on save.
"""

from __future__ import annotations

import nh3

_ALLOWED_TAGS: frozenset[str] = frozenset(
    {
        "a", "abbr", "b", "blockquote", "br", "code", "em", "figcaption",
        "figure", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "li",
        "ol", "p", "pre", "s", "span", "strong", "sub", "sup", "table",
        "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul", "div",
    }
)

_ALLOWED_ATTRS: dict[str, set[str]] = {
    # `rel` is added by nh3 via `link_rel=` - including it here is rejected.
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "title", "width", "height", "loading"},
    "code": {"class"},  # language-* for syntax highlighting
    "pre": {"class"},
    "th": {"colspan", "rowspan", "scope"},
    "td": {"colspan", "rowspan"},
    "span": {"class"},
    "div": {"class"},
}

_ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https", "mailto"})


def clean_html(html: str) -> str:
    """Return a sanitised copy of `html`. Strips disallowed tags/attrs entirely."""
    return nh3.clean(
        html,
        tags=set(_ALLOWED_TAGS),
        attributes=_ALLOWED_ATTRS,
        url_schemes=set(_ALLOWED_SCHEMES),
        link_rel="noopener noreferrer nofollow",
    )

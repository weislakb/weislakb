#!/usr/bin/env python3
"""Read HTML from stdin and print Markdown to stdout.

Uses markdownify when available, falls back to a minimal regex-based
conversion so the skill still works without extra pip dependencies.
"""

import re
import sys


def _strip_tags(html: str, tags: list[str]) -> str:
    """Remove specified HTML tags and their contents."""
    for tag in tags:
        html = re.sub(
            rf"<{tag}[\s>].*?</{tag}>",
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
    return html


def _minimal_convert(html: str) -> str:
    """Best-effort HTML→Markdown without external libraries."""
    html = _strip_tags(html, ["script", "style", "nav", "footer", "noscript", "svg", "header"])

    # Headings
    for level in range(6, 0, -1):
        html = re.sub(
            rf"<h{level}[^>]*>(.*?)</h{level}>",
            lambda m, l=level: f"\n{'#' * l} {m.group(1).strip()}\n",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

    # Links
    html = re.sub(
        r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        r"[\2](\1)",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Images
    html = re.sub(
        r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/?>',
        r"![\2](\1)",
        html,
        flags=re.IGNORECASE,
    )

    # Bold / italic
    html = re.sub(r"<(strong|b)>(.*?)</\1>", r"**\2**", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<(em|i)>(.*?)</\1>", r"*\2*", html, flags=re.DOTALL | re.IGNORECASE)

    # Code
    html = re.sub(r"<code>(.*?)</code>", r"`\1`", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(
        r"<pre[^>]*>(.*?)</pre>",
        lambda m: f"\n```\n{m.group(1).strip()}\n```\n",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Lists
    html = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", html, flags=re.DOTALL | re.IGNORECASE)

    # Paragraphs / breaks
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<hr[^>]*/?>", "\n---\n", html, flags=re.IGNORECASE)

    # Tables (basic)
    html = re.sub(r"<tr[^>]*>(.*?)</tr>", lambda m: m.group(1) + "\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<t[hd][^>]*>(.*?)</t[hd]>", r"| \1 ", html, flags=re.DOTALL | re.IGNORECASE)

    # Strip remaining tags
    html = re.sub(r"<[^>]+>", "", html)

    # Decode common entities
    for entity, char in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " ")]:
        html = html.replace(entity, char)

    # Collapse whitespace
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def convert(html: str) -> str:
    """Convert HTML to Markdown, using markdownify if available."""
    try:
        from markdownify import markdownify

        md = markdownify(
            html,
            heading_style="ATX",
            strip=["script", "style", "nav", "footer", "noscript", "svg", "header"],
        )
        return re.sub(r"\n{3,}", "\n\n", md).strip()
    except ImportError:
        return _minimal_convert(html)


if __name__ == "__main__":
    html_input = sys.stdin.read()
    if not html_input.strip():
        print("(empty input)", file=sys.stderr)
        sys.exit(1)
    print(convert(html_input))

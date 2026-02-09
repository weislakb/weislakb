"""HTML to Markdown conversion utilities."""

from __future__ import annotations

import json
import re

from markdownify import markdownify


def html_to_markdown(html: str, *, strip_tags: list[str] | None = None) -> str:
    """Convert *html* to Markdown using markdownify.

    Parameters
    ----------
    html:
        Raw HTML string.
    strip_tags:
        HTML tags to remove entirely (e.g. ``["script", "style"]``).
        Defaults to script, style, nav, footer, and header.
    """
    if strip_tags is None:
        strip_tags = ["script", "style", "nav", "footer", "header", "noscript", "svg"]

    md: str = markdownify(
        html,
        heading_style="ATX",
        strip=strip_tags,
    )

    # Collapse excessive blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)

    return md.strip()


def html_to_markdown_tool(html: str) -> str:
    """Tool-use wrapper — returns a JSON string consumable by the agent."""
    md = html_to_markdown(html)
    return json.dumps({"markdown": md})

#!/usr/bin/env python3
"""Convert HTML to Markdown.

Reads HTML from a file path (argument) or stdin and prints Markdown to stdout.

Usage:
    python3 html_to_markdown.py page.html
    python3 html_to_markdown.py --builtin page.html   # force builtin converter
    cat page.html | python3 html_to_markdown.py
"""

import argparse
import html as html_module
import re
import sys


def _strip_tags(text: str, tags: list[str]) -> str:
    """Remove specified HTML tags and their contents."""
    for tag in tags:
        text = re.sub(
            rf"<{tag}[\s>].*?</{tag}>",
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
    return text


STRIP_TAGS = ["script", "style", "nav", "footer", "noscript", "svg", "header"]


def _builtin_convert(raw: str) -> str:
    """Best-effort HTML to Markdown without external libraries."""
    raw = _strip_tags(raw, STRIP_TAGS)

    # Headings (process h6 down to h1 so nested headings work)
    for level in range(6, 0, -1):
        raw = re.sub(
            rf"<h{level}[^>]*>(.*?)</h{level}>",
            lambda m, lv=level: f"\n{'#' * lv} {m.group(1).strip()}\n",
            raw,
            flags=re.DOTALL | re.IGNORECASE,
        )

    # Links — handle both single and double quoted href
    raw = re.sub(
        r"""<a[^>]*href=["']([^"']*)["'][^>]*>(.*?)</a>""",
        r"[\2](\1)",
        raw,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Images
    raw = re.sub(
        r"""<img[^>]*src=["']([^"']*)["'][^>]*alt=["']([^"']*)["'][^>]*/?>""",
        r"![\2](\1)",
        raw,
        flags=re.IGNORECASE,
    )
    # Images without alt before src
    raw = re.sub(
        r"""<img[^>]*alt=["']([^"']*)["'][^>]*src=["']([^"']*)["'][^>]*/?>""",
        r"![\1](\2)",
        raw,
        flags=re.IGNORECASE,
    )

    # Bold / italic
    raw = re.sub(r"<(strong|b)>(.*?)</\1>", r"**\2**", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"<(em|i)>(.*?)</\1>", r"*\2*", raw, flags=re.DOTALL | re.IGNORECASE)

    # Code blocks (pre before inline code)
    raw = re.sub(
        r"<pre[^>]*><code[^>]*>(.*?)</code></pre>",
        lambda m: f"\n```\n{m.group(1).strip()}\n```\n",
        raw,
        flags=re.DOTALL | re.IGNORECASE,
    )
    raw = re.sub(
        r"<pre[^>]*>(.*?)</pre>",
        lambda m: f"\n```\n{m.group(1).strip()}\n```\n",
        raw,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Inline code
    raw = re.sub(r"<code>(.*?)</code>", r"`\1`", raw, flags=re.DOTALL | re.IGNORECASE)

    # Lists
    raw = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"</?[ou]l[^>]*>", "", raw, flags=re.IGNORECASE)

    # Paragraphs / breaks
    raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    raw = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", raw, flags=re.DOTALL | re.IGNORECASE)
    raw = re.sub(r"<hr[^>]*/?>", "\n---\n", raw, flags=re.IGNORECASE)

    # Tables (basic)
    raw = re.sub(
        r"<tr[^>]*>(.*?)</tr>",
        lambda m: m.group(1) + "\n",
        raw,
        flags=re.DOTALL | re.IGNORECASE,
    )
    raw = re.sub(r"<t[hd][^>]*>(.*?)</t[hd]>", r"| \1 ", raw, flags=re.DOTALL | re.IGNORECASE)

    # Strip remaining tags
    raw = re.sub(r"<[^>]+>", "", raw)

    # Decode HTML entities
    raw = html_module.unescape(raw)

    # Collapse runs of blank lines
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    # Collapse runs of spaces (but not newlines)
    raw = re.sub(r"[^\S\n]+", " ", raw)

    return raw.strip()


def convert(raw: str, *, force_builtin: bool = False) -> str:
    """Convert HTML to Markdown.

    Uses markdownify if installed, otherwise the builtin converter.
    Pass force_builtin=True to skip the markdownify attempt.
    """
    if not force_builtin:
        try:
            from markdownify import markdownify

            md = markdownify(
                raw,
                heading_style="ATX",
                strip=STRIP_TAGS,
                convert_as_inline=False,
                autolinks=True,
                escape_asterisks=False,
                escape_underscores=False,
            )
            # Collapse excessive blank lines
            md = re.sub(r"\n{3,}", "\n\n", md)
            return md.strip()
        except (ImportError, Exception) as exc:
            # markdownify not installed or crashed — fall through to builtin
            print(f"markdownify unavailable ({exc}), using builtin converter", file=sys.stderr)

    return _builtin_convert(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert HTML to Markdown")
    parser.add_argument("file", nargs="?", help="HTML file to convert (reads stdin if omitted)")
    parser.add_argument(
        "--builtin",
        action="store_true",
        help="Force the builtin converter (skip markdownify)",
    )
    args = parser.parse_args()

    # Read input
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
        except FileNotFoundError:
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        print("(empty input)", file=sys.stderr)
        sys.exit(1)

    print(convert(raw, force_builtin=args.builtin))


if __name__ == "__main__":
    main()

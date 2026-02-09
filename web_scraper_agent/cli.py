"""CLI entrypoint for the web scraper agent."""

from __future__ import annotations

import argparse
import sys

from .agent import run_agent
from .credentials import get_credentials


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="web-scraper-agent",
        description=(
            "Claude-powered agent that logs into a website, scrapes a page, "
            "and returns the content as Markdown."
        ),
    )
    parser.add_argument(
        "url",
        help="URL of the page to scrape.",
    )
    parser.add_argument(
        "--login-url",
        default=None,
        help="Login page URL (defaults to the target URL).",
    )
    parser.add_argument(
        "--page-url",
        default=None,
        help="Page to navigate to after login, if different from the target URL.",
    )
    parser.add_argument(
        "--username-env",
        default="SCRAPER_USERNAME",
        help="Environment variable name for the username (default: SCRAPER_USERNAME).",
    )
    parser.add_argument(
        "--password-env",
        default="SCRAPER_PASSWORD",
        help="Environment variable name for the password (default: SCRAPER_PASSWORD).",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="Anthropic model to use (default: claude-sonnet-4-20250514).",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run the browser with a visible window (useful for debugging).",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Write Markdown output to this file instead of stdout.",
    )

    args = parser.parse_args(argv)

    # --- credentials ----------------------------------------------------------
    username, password = get_credentials(
        username_env=args.username_env,
        password_env=args.password_env,
    )

    # --- run agent ------------------------------------------------------------
    print("Starting web scraper agent...", file=sys.stderr)

    markdown = run_agent(
        target_url=args.url,
        login_url=args.login_url,
        username=username,
        password=password,
        headless=not args.no_headless,
        model=args.model,
        page_url=args.page_url,
    )

    # --- output ---------------------------------------------------------------
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(markdown)
        print(f"Markdown written to {args.output}", file=sys.stderr)
    else:
        print(markdown)


if __name__ == "__main__":
    main()

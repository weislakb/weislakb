"""Playwright-backed browser tool that the Claude agent invokes via tool-use."""

from __future__ import annotations

import json
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


class BrowserTool:
    """Wraps a headless Chromium browser and exposes actions the agent can call."""

    def __init__(self, headless: bool = True) -> None:
        self._headless = headless
        self._pw_ctx = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    # -- lifecycle ------------------------------------------------------------

    def start(self) -> None:
        """Launch the browser (idempotent)."""
        if self._browser is not None:
            return
        self._pw_ctx = sync_playwright().start()
        self._browser = self._pw_ctx.chromium.launch(headless=self._headless)
        self._context = self._browser.new_context()
        self._page = self._context.new_page()

    def stop(self) -> None:
        """Tear down the browser."""
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._pw_ctx is not None:
            self._pw_ctx.stop()
            self._pw_ctx = None
        self._context = None
        self._page = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    # -- tool implementations -------------------------------------------------

    def navigate(self, url: str) -> str:
        """Navigate to *url* and return the final URL after redirects."""
        self.page.goto(url, wait_until="networkidle")
        return json.dumps({"url": self.page.url, "title": self.page.title()})

    def login(
        self,
        login_url: str,
        username: str,
        password: str,
        username_selector: str = 'input[name="username"], input[type="email"], #username, #email',
        password_selector: str = 'input[name="password"], input[type="password"], #password',
        submit_selector: str = 'button[type="submit"], input[type="submit"]',
    ) -> str:
        """Fill in a login form and submit it.

        The selectors use CSS and default to common patterns.  The agent can
        override them if the page uses non-standard markup.
        """
        self.page.goto(login_url, wait_until="networkidle")

        # Try each selector in the comma-separated list
        username_field = self._find_first(username_selector)
        if username_field is None:
            return json.dumps({"success": False, "error": "Username field not found"})

        password_field = self._find_first(password_selector)
        if password_field is None:
            return json.dumps({"success": False, "error": "Password field not found"})

        username_field.fill(username)
        password_field.fill(password)

        submit_btn = self._find_first(submit_selector)
        if submit_btn:
            submit_btn.click()
        else:
            password_field.press("Enter")

        self.page.wait_for_load_state("networkidle")

        return json.dumps({
            "success": True,
            "url": self.page.url,
            "title": self.page.title(),
        })

    def get_page_html(self) -> str:
        """Return the full HTML of the current page."""
        html = self.page.content()
        return json.dumps({"url": self.page.url, "html": html})

    def screenshot(self, path: str = "screenshot.png") -> str:
        """Save a screenshot and return the file path."""
        self.page.screenshot(path=path, full_page=True)
        return json.dumps({"path": path})

    def click(self, selector: str) -> str:
        """Click the first element matching *selector*."""
        self.page.click(selector)
        self.page.wait_for_load_state("networkidle")
        return json.dumps({"url": self.page.url, "title": self.page.title()})

    def fill(self, selector: str, value: str) -> str:
        """Fill an input field."""
        self.page.fill(selector, value)
        return json.dumps({"filled": True})

    def get_text(self, selector: str = "body") -> str:
        """Return the inner text of the matched element."""
        text = self.page.inner_text(selector)
        # Truncate very large text to avoid blowing up context
        if len(text) > 50_000:
            text = text[:50_000] + "\n... [truncated]"
        return json.dumps({"text": text})

    # -- helpers ---------------------------------------------------------------

    def _find_first(self, selectors: str):
        """Given a comma-separated selector list, return the first match."""
        for sel in selectors.split(","):
            sel = sel.strip()
            loc = self.page.locator(sel)
            if loc.count() > 0:
                return loc.first
        return None

    # -- tool-use schema (used by the agent) -----------------------------------

    @staticmethod
    def tool_definitions() -> list[dict[str, Any]]:
        """Return Anthropic tool-use definitions for every browser action."""
        return [
            {
                "name": "browser_navigate",
                "description": "Navigate the browser to a URL. Returns the final URL and page title.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to navigate to."},
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "browser_login",
                "description": (
                    "Navigate to a login page, fill in credentials, and submit. "
                    "CSS selectors can be overridden if the defaults don't match."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "login_url": {"type": "string", "description": "URL of the login page."},
                        "username_selector": {
                            "type": "string",
                            "description": "CSS selector for the username field (comma-separated fallbacks).",
                        },
                        "password_selector": {
                            "type": "string",
                            "description": "CSS selector for the password field (comma-separated fallbacks).",
                        },
                        "submit_selector": {
                            "type": "string",
                            "description": "CSS selector for the submit button (comma-separated fallbacks).",
                        },
                    },
                    "required": ["login_url"],
                },
            },
            {
                "name": "browser_get_html",
                "description": "Return the full HTML source of the current page.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "browser_screenshot",
                "description": "Take a full-page screenshot and save it to a file.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path for the screenshot (default: screenshot.png).",
                        },
                    },
                },
            },
            {
                "name": "browser_click",
                "description": "Click the first element matching a CSS selector.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector of the element to click."},
                    },
                    "required": ["selector"],
                },
            },
            {
                "name": "browser_fill",
                "description": "Fill an input field identified by a CSS selector.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector of the input field."},
                        "value": {"type": "string", "description": "Value to type into the field."},
                    },
                    "required": ["selector", "value"],
                },
            },
            {
                "name": "browser_get_text",
                "description": "Get the visible inner text of an element (defaults to <body>).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector (default: body).",
                        },
                    },
                },
            },
            {
                "name": "convert_html_to_markdown",
                "description": (
                    "Convert raw HTML to clean Markdown. Use this after browser_get_html "
                    "to produce a readable Markdown document."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "html": {"type": "string", "description": "The HTML string to convert."},
                    },
                    "required": ["html"],
                },
            },
        ]

"""Core agent loop — drives Claude with browser tools to scrape web pages."""

from __future__ import annotations

import json
from typing import Any

import anthropic

from .browser_tool import BrowserTool
from .converter import html_to_markdown_tool

MODEL = "claude-sonnet-4-20250514"
MAX_TURNS = 25


def _build_system_prompt(username: str, has_password: bool) -> str:
    return (
        "You are a web-scraping agent. You have access to a headless browser.\n"
        "Your goal is to:\n"
        "  1. Navigate to the target website.\n"
        "  2. Log in using the provided credentials.\n"
        "  3. Navigate to the requested page (if different from the landing page).\n"
        "  4. Retrieve the full HTML of the page.\n"
        "  5. Convert that HTML to clean Markdown.\n"
        "  6. Return the Markdown to the user.\n\n"
        "Credentials have already been collected and will be injected into the\n"
        "browser_login tool automatically — you do NOT need to ask for them.\n"
        "Just call browser_login with the login_url (and optional selectors).\n\n"
        "Always call convert_html_to_markdown after getting HTML so the user\n"
        "receives readable Markdown output.\n\n"
        "If login fails, try adjusting the CSS selectors based on what you see\n"
        "on the page (use browser_get_text to inspect visible content).\n"
    )


def _dispatch_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    browser: BrowserTool,
    username: str,
    password: str,
) -> str:
    """Route a tool call to the correct implementation and return the result."""
    if tool_name == "browser_navigate":
        return browser.navigate(tool_input["url"])

    if tool_name == "browser_login":
        kwargs: dict[str, Any] = {
            "login_url": tool_input["login_url"],
            "username": username,
            "password": password,
        }
        for key in ("username_selector", "password_selector", "submit_selector"):
            if key in tool_input:
                kwargs[key] = tool_input[key]
        return browser.login(**kwargs)

    if tool_name == "browser_get_html":
        return browser.get_page_html()

    if tool_name == "browser_screenshot":
        return browser.screenshot(tool_input.get("path", "screenshot.png"))

    if tool_name == "browser_click":
        return browser.click(tool_input["selector"])

    if tool_name == "browser_fill":
        return browser.fill(tool_input["selector"], tool_input["value"])

    if tool_name == "browser_get_text":
        return browser.get_text(tool_input.get("selector", "body"))

    if tool_name == "convert_html_to_markdown":
        return html_to_markdown_tool(tool_input["html"])

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def run_agent(
    *,
    target_url: str,
    login_url: str | None = None,
    username: str,
    password: str,
    headless: bool = True,
    model: str = MODEL,
    page_url: str | None = None,
) -> str:
    """Run the scraping agent and return the final Markdown content.

    Parameters
    ----------
    target_url:
        The page whose content should be scraped and converted.
    login_url:
        The login page URL.  Defaults to *target_url* if not given.
    username / password:
        Credentials for the login form.
    headless:
        Whether to run the browser in headless mode.
    model:
        Anthropic model to use for the agent brain.
    page_url:
        Optional separate page to navigate to after login (if different
        from *target_url*).
    """
    if login_url is None:
        login_url = target_url

    client = anthropic.Anthropic()
    browser = BrowserTool(headless=headless)
    browser.start()

    tools = BrowserTool.tool_definitions()
    system = _build_system_prompt(username, bool(password))

    user_message = (
        f"Please log in at {login_url} and then scrape the page at "
        f"{page_url or target_url}.  Return the page content as Markdown."
    )

    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

    final_text = ""

    try:
        for _turn in range(MAX_TURNS):
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system,
                tools=tools,
                messages=messages,
            )

            # Collect any text blocks the model produced
            assistant_text_parts: list[str] = []
            tool_use_blocks: list[Any] = []

            for block in response.content:
                if block.type == "text":
                    assistant_text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_use_blocks.append(block)

            # Append the full assistant turn
            messages.append({"role": "assistant", "content": response.content})

            # If the model stopped without tool calls, we're done
            if response.stop_reason == "end_turn" or not tool_use_blocks:
                final_text = "\n".join(assistant_text_parts)
                break

            # Execute each tool call and feed results back
            tool_results: list[dict[str, Any]] = []
            for tool_block in tool_use_blocks:
                result_str = _dispatch_tool(
                    tool_block.name,
                    tool_block.input,
                    browser,
                    username,
                    password,
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result_str,
                })

            messages.append({"role": "user", "content": tool_results})
    finally:
        browser.stop()

    return final_text

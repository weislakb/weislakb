# Web Scraper Agent

A Claude-powered agent that uses a headless browser to log into websites, scrape pages, and convert the HTML content to Markdown.

## Architecture

```
User ──▶ CLI ──▶ Claude Agent (tool-use loop) ──▶ Browser Tool (Playwright)
                        │                                  │
                        │                                  ▼
                        │                          HTML page content
                        │                                  │
                        ▼                                  ▼
                  Markdown output  ◀──────  HTML→Markdown converter
```

The agent uses Claude as its "brain" via the Anthropic API with tool-use. Claude decides which browser actions to take (navigate, login, click, scrape) and orchestrates the full workflow autonomously.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Credentials

The agent needs credentials to log into the target website. Two methods are supported:

### 1. Environment variables (non-interactive)

```bash
export SCRAPER_USERNAME="myuser"
export SCRAPER_PASSWORD="mypassword"
```

Custom env var names can be specified:

```bash
export MY_USER="admin"
export MY_PASS="secret"
python -m web_scraper_agent https://example.com --username-env MY_USER --password-env MY_PASS
```

### 2. Interactive prompt

If the environment variables are not set, the agent will prompt for username and password on stdin (password input is hidden).

## Usage

```bash
# Basic: login and scrape the same URL
python -m web_scraper_agent https://example.com/dashboard

# Separate login page and target page
python -m web_scraper_agent https://example.com/dashboard \
    --login-url https://example.com/login

# Navigate to a different page after login
python -m web_scraper_agent https://example.com \
    --login-url https://example.com/login \
    --page-url https://example.com/reports

# Save output to a file
python -m web_scraper_agent https://example.com/dashboard -o output.md

# Run with visible browser (for debugging)
python -m web_scraper_agent https://example.com/dashboard --no-headless
```

## Options

| Flag | Description |
|------|-------------|
| `url` | URL of the page to scrape (positional) |
| `--login-url` | Login page URL (defaults to target URL) |
| `--page-url` | Page to navigate to after login |
| `--username-env` | Env var name for username (default: `SCRAPER_USERNAME`) |
| `--password-env` | Env var name for password (default: `SCRAPER_PASSWORD`) |
| `--model` | Anthropic model to use (default: `claude-sonnet-4-20250514`) |
| `--no-headless` | Show the browser window |
| `-o, --output` | Write Markdown to a file instead of stdout |

## Project Structure

```
web_scraper_agent/
  __init__.py       # Package marker
  __main__.py       # python -m entrypoint
  agent.py          # Claude agent loop with tool dispatch
  browser_tool.py   # Playwright browser wrapper + tool schemas
  cli.py            # Argument parsing and orchestration
  converter.py      # HTML → Markdown conversion
  credentials.py    # Credential resolution (env vars / prompt)
requirements.txt
```

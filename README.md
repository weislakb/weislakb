# get-web-page — Claude Code Skill

A Claude Code skill that uses [Vercel agent-browser](https://github.com/vercel-labs/agent-browser) to log into websites, scrape authenticated pages, and return clean Markdown content — all from within a Claude Code session.

## How it works

```
User invokes /get-web-page <login-url> [page-url]
        │
        ▼
Extract domain from URL (e.g. app.example.com)
        │
        ├── Profile exists (~/.claude/browser-profiles/<domain>/)
        │       → skip login, reuse session cookies
        │
        └── No profile → resolve credentials:
                1. macOS Keychain (get-web-page/<domain>)
                2. Env vars (APP_EXAMPLE_COM_USERNAME or SCRAPER_USERNAME)
                3. Ask the user
                        │
                        ▼
                agent-browser --profile ... open <login-url>
                agent-browser snapshot -i    ← identify form fields
                agent-browser fill / click   ← log in
                        │
                        ▼
                Profile saved automatically for next time
                Offer to save credentials to Keychain
        │
        ▼
agent-browser --profile ... open <page-url>
agent-browser get html body > /tmp/scrape_output.html
        │
        ▼
python3 html_to_markdown.py /tmp/scrape_output.html
        │
        ▼
Markdown returned to conversation
```

## Prerequisites

Install `agent-browser` globally:

```bash
npm install -g agent-browser
agent-browser install
```

Optionally, for higher-quality HTML-to-Markdown conversion:

```bash
pip install markdownify
```

The skill includes a built-in fallback converter that works with only the Python standard library.

## Credentials

Credentials are resolved per-domain in this order:

### 1. Persistent browser profile (best — no credentials needed)

After logging in once, agent-browser saves session cookies to `~/.claude/browser-profiles/<domain>/`. Subsequent runs skip the login flow entirely.

### 2. macOS Keychain

Store credentials in the Keychain under service `get-web-page/<domain>`:

```bash
security add-generic-password -s "get-web-page/app.example.com" -a "user@example.com" -w "mypassword" -U
```

The skill looks these up automatically. Credentials never touch env vars or shell history.

### 3. Environment variables

Domain-specific (dots/hyphens become underscores, uppercased):

```bash
export APP_EXAMPLE_COM_USERNAME="user@example.com"
export APP_EXAMPLE_COM_PASSWORD="mypassword"
```

Or generic fallback:

```bash
export SCRAPER_USERNAME="user@example.com"
export SCRAPER_PASSWORD="mypassword"
```

### 4. Interactive prompt

If nothing else is configured, the skill asks you directly and offers to save to Keychain afterward.

## Usage

Inside a Claude Code session:

```
# Login and scrape the post-login page
/get-web-page https://myapp.com/login

# Login, then navigate to a specific page
/get-web-page https://myapp.com/login https://myapp.com/dashboard/reports
```

After the skill runs, the Markdown content is in the conversation for Claude to summarize, extract data, compare, etc.

## Skill structure

```
.claude/skills/get-web-page/
├── SKILL.md                      # Agent instructions (credential resolution,
│                                 #   profile management, login flow, scrape, convert)
└── scripts/
    └── html_to_markdown.py       # HTML → Markdown converter
```

| File | Purpose |
|------|---------|
| `SKILL.md` | Step-by-step instructions Claude follows: domain extraction, profile check, keychain/env/prompt credential resolution, agent-browser login, HTML extraction, Markdown conversion |
| `html_to_markdown.py` | Reads HTML from a file or stdin, outputs Markdown. Uses `markdownify` if installed, gracefully falls back to a built-in regex converter. Supports `--builtin` flag to force the fallback |

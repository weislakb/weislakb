# get-web-page — Claude Code Skill

A Claude Code skill that uses [Vercel agent-browser](https://github.com/vercel-labs/agent-browser) to log into websites, scrape authenticated pages, and return clean Markdown content — all from within a Claude Code session.

## How it works

```
User invokes /get-web-page
        │
        ▼
Claude reads SKILL.md instructions
        │
        ▼
agent-browser open <login-url>       ← headless Chromium
agent-browser snapshot -i            ← find form fields
agent-browser fill / click           ← log in with credentials
        │
        ▼
agent-browser open <page-url>        ← navigate to target
agent-browser get html body          ← extract HTML
        │
        ▼
html_to_markdown.py                  ← convert to Markdown
        │
        ▼
Markdown returned to conversation    ← Claude continues working
```

Claude Code acts as the agent brain — it reads the snapshot, decides which fields to fill, adapts to different login forms, and handles errors.

## Prerequisites

Install `agent-browser` globally:

```bash
npm install -g agent-browser
agent-browser install
```

Optionally, for higher-quality HTML→Markdown conversion:

```bash
pip install markdownify
```

(The skill includes a built-in fallback converter that works without any Python dependencies beyond the standard library.)

## Credentials

Set credentials via environment variables before starting Claude Code:

```bash
export SCRAPER_USERNAME="user@example.com"
export SCRAPER_PASSWORD="mypassword"
```

If these are not set, the skill will ask you for them interactively during the session.

## Usage

Inside a Claude Code session:

```
/get-web-page https://myapp.com/login
```

Login and then scrape a different page:

```
/get-web-page https://myapp.com/login https://myapp.com/dashboard/reports
```

After the skill runs, the Markdown content is available in the conversation. You can then ask Claude to summarize it, extract data, compare pages, etc.

## Skill structure

```
.claude/skills/get-web-page/
├── SKILL.md                      # Skill instructions (the agent prompt)
└── scripts/
    └── html_to_markdown.py       # HTML → Markdown converter
```

| File | Purpose |
|------|---------|
| `SKILL.md` | Step-by-step instructions Claude follows: resolve credentials, open login page, snapshot the form, fill & submit, navigate, extract HTML, convert to Markdown |
| `html_to_markdown.py` | Reads HTML from stdin, outputs Markdown. Uses `markdownify` if installed, otherwise a built-in regex-based converter |

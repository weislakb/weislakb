---
name: get-web-page
description: Log into a website using agent-browser, scrape a page, and return its content as Markdown. Use when a user needs to fetch authenticated web page content.
argument-hint: <login-url> [page-url]
allowed-tools: Bash(agent-browser *), Read
---

# Get Web Page (Authenticated Scrape → Markdown)

Scrape an authenticated web page and return clean Markdown content.

## Arguments

- `$ARGUMENTS[0]` — the login URL (required)
- `$ARGUMENTS[1]` — the page URL to scrape after login (optional, defaults to the post-login page)

## Credentials

Credentials come from environment variables. Check for them first:

- `SCRAPER_USERNAME` — the username / email
- `SCRAPER_PASSWORD` — the password

If either is missing, **ask the user** before proceeding. Never hardcode credentials.

## Workflow

Follow these steps exactly. Use `agent-browser` CLI for all browser interactions.

### Step 1 — Resolve credentials

```bash
echo "USERNAME=${SCRAPER_USERNAME:-(not set)}"
echo "PASSWORD=${SCRAPER_PASSWORD:+(set)}"
```

If either is `(not set)`, stop and ask the user to provide the value.

### Step 2 — Open the login page

```bash
agent-browser open "$ARGUMENTS[0]"
```

### Step 3 — Identify form fields

Take a snapshot of interactive elements to find the username, password, and submit controls:

```bash
agent-browser snapshot -i
```

Read the snapshot output. Identify:
- The **username / email** field (look for `textbox` with name like "email", "username", "login", or similar)
- The **password** field (look for `textbox` or input with name "password")
- The **submit** button (look for `button` with name like "Sign in", "Log in", "Submit")

### Step 4 — Fill credentials and submit

Use the refs from the snapshot. For example, if the email field is `@e3`, password is `@e4`, and submit is `@e5`:

```bash
agent-browser fill @e3 "$SCRAPER_USERNAME"
agent-browser fill @e4 "$SCRAPER_PASSWORD"
agent-browser click @e5
```

Adapt the refs to match what the snapshot actually shows.

### Step 5 — Wait for login to complete

```bash
agent-browser wait --load networkidle
```

Verify login succeeded by checking the page:

```bash
agent-browser get title
agent-browser get url
```

If the URL still shows the login page or the title indicates an error, report the failure to the user.

### Step 6 — Navigate to target page (if specified)

If `$ARGUMENTS[1]` was provided and differs from the current URL:

```bash
agent-browser open "$ARGUMENTS[1]"
agent-browser wait --load networkidle
```

### Step 7 — Extract the page HTML

```bash
agent-browser get html body
```

### Step 8 — Convert HTML to Markdown

Run the conversion script included with this skill:

```bash
echo '<the html from step 7>' | python3 .claude/skills/get-web-page/scripts/html_to_markdown.py
```

If the python script is not available or fails, use this inline fallback:

```bash
agent-browser get html body | python3 -c "
import sys
try:
    from markdownify import markdownify
    html = sys.stdin.read()
    print(markdownify(html, heading_style='ATX', strip=['script','style','nav','footer','noscript','svg']))
except ImportError:
    print(sys.stdin.read())
"
```

### Step 9 — Return the Markdown

Output the final Markdown content. This is now available for further processing in the conversation.

### Step 10 — Clean up

```bash
agent-browser close
```

## Error Handling

- If `agent-browser` is not installed, tell the user to install it: `npm install -g agent-browser && agent-browser install`
- If login fails (page stays on login URL, error message visible), report the specific error and ask the user for guidance
- If the target page returns empty HTML, try `agent-browser snapshot` to see what's on the page and report back
- If HTML-to-Markdown conversion fails, return the raw HTML instead

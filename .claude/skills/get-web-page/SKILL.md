---
name: get-web-page
description: Log into a website using agent-browser, scrape a page, and return its content as Markdown. Use when a user needs to fetch authenticated web page content.
argument-hint: <login-url> [page-url]
allowed-tools: Bash(agent-browser *), Bash(security *), Bash(python3 *), Read
---

# Get Web Page (Authenticated Scrape → Markdown)

Scrape an authenticated web page and return clean Markdown content.

## Arguments

- `$ARGUMENTS[0]` — the login URL (required)
- `$ARGUMENTS[1]` — the page URL to scrape after login (optional, defaults to the post-login page)

## Step 1 — Extract the domain

Parse the domain from `$ARGUMENTS[0]`. For example:
- `https://app.example.com/login` → `app.example.com`
- `https://mysite.io/auth/signin` → `mysite.io`

This domain is used for profile directories and keychain lookups throughout.

## Step 2 — Check for an existing browser profile

Profiles live at `~/.claude/browser-profiles/<domain>/`. If a profile exists,
the user has logged in before and we can skip credential resolution entirely.

```bash
ls ~/.claude/browser-profiles/<domain>/ 2>/dev/null && echo "PROFILE_EXISTS" || echo "NO_PROFILE"
```

If `PROFILE_EXISTS`, **skip to Step 5** — no credentials needed.

## Step 3 — Resolve credentials (only if no profile)

Try each source in order. Stop at the first one that provides **both** username and password.

### 3a — macOS Keychain

Look up credentials stored under the service name `get-web-page/<domain>`:

```bash
security find-generic-password -s "get-web-page/<domain>" -g 2>&1
```

Parse the output:
- The **account** field (`"acct"<blob>=`) is the username.
- The **password** field (`password:`) is the password.

If both are found, use them. If the `security` command fails or is not available (Linux), move on.

### 3b — Environment variables

Check domain-specific env vars first, then generic ones:

```bash
# Domain-specific (dots/hyphens replaced with underscores, uppercased)
# e.g. app.example.com → APP_EXAMPLE_COM_USERNAME
DOMAIN_VAR=$(echo "<domain>" | tr '.-' '__' | tr '[:lower:]' '[:upper:]')
eval "echo \${${DOMAIN_VAR}_USERNAME:-(not set)}"
eval "echo \${${DOMAIN_VAR}_PASSWORD:+(set)}"

# Generic fallback
echo "${SCRAPER_USERNAME:-(not set)}"
echo "${SCRAPER_PASSWORD:+(set)}"
```

If credentials are found (either domain-specific or generic), use them.

### 3c — Ask the user

If no credentials were found from any source, **stop and ask the user**.
Tell them which domain you need credentials for and offer to store them:

> I need credentials for `<domain>`. Please provide a username and password.
> After login, I'll save the browser session so you won't need to enter them again.
> Optionally I can also store them in your macOS Keychain for future use.

Do NOT proceed until the user provides credentials.

## Step 4 — Login with agent-browser

### 4a — Open the login page with a profile directory

Always use `--profile` so the session persists:

```bash
agent-browser --profile ~/.claude/browser-profiles/<domain> open "$ARGUMENTS[0]"
```

### 4b — Identify form fields

```bash
agent-browser --profile ~/.claude/browser-profiles/<domain> snapshot -i
```

Read the output. Identify:
- The **username / email** field (textbox named "email", "username", "login", etc.)
- The **password** field (textbox named "password")
- The **submit** button (button named "Sign in", "Log in", "Submit", etc.)

### 4c — Fill and submit

Use the refs from the snapshot. **IMPORTANT**: pass credentials via env vars to avoid
them appearing in shell history or process listings:

```bash
CRED_USER='<username>' agent-browser --profile ~/.claude/browser-profiles/<domain> eval "document.querySelector('<username_css_selector>').value = process.env.CRED_USER"
CRED_PASS='<password>' agent-browser --profile ~/.claude/browser-profiles/<domain> eval "document.querySelector('<password_css_selector>').value = process.env.CRED_PASS"
```

If the eval approach doesn't trigger the form's change events, fall back to fill with refs:

```bash
agent-browser --profile ~/.claude/browser-profiles/<domain> fill @<ref> "<username>"
agent-browser --profile ~/.claude/browser-profiles/<domain> fill @<ref> "<password>"
agent-browser --profile ~/.claude/browser-profiles/<domain> click @<ref>
```

### 4d — Wait and verify

```bash
agent-browser --profile ~/.claude/browser-profiles/<domain> wait --load networkidle
agent-browser --profile ~/.claude/browser-profiles/<domain> get title
agent-browser --profile ~/.claude/browser-profiles/<domain> get url
```

If the URL still shows the login page or the title indicates an error, report the failure.

### 4e — Offer to save credentials to Keychain

After a successful login, if credentials came from the user prompt or env vars (not Keychain),
ask the user if they want to save to macOS Keychain for future use:

> Login succeeded! Want me to save these credentials to your macOS Keychain
> (service: `get-web-page/<domain>`) so you don't need to enter them next time?

If they agree:

```bash
security add-generic-password -s "get-web-page/<domain>" -a "<username>" -w "<password>" -U
```

The browser profile is always saved automatically by `--profile`.

## Step 5 — Navigate to the target page

If `$ARGUMENTS[1]` was provided:

```bash
agent-browser --profile ~/.claude/browser-profiles/<domain> open "$ARGUMENTS[1]"
agent-browser --profile ~/.claude/browser-profiles/<domain> wait --load networkidle
```

Otherwise, just confirm the current page after login:

```bash
agent-browser --profile ~/.claude/browser-profiles/<domain> get url
```

## Step 6 — Extract the page HTML

```bash
agent-browser --profile ~/.claude/browser-profiles/<domain> get html body > /tmp/scrape_output.html
```

## Step 7 — Convert HTML to Markdown

Pipe the saved HTML file through the conversion script:

```bash
python3 .claude/skills/get-web-page/scripts/html_to_markdown.py /tmp/scrape_output.html
```

If the script fails, use the inline fallback (no dependencies):

```bash
python3 .claude/skills/get-web-page/scripts/html_to_markdown.py --builtin /tmp/scrape_output.html
```

## Step 8 — Return the Markdown

Output the final Markdown content. This is now available for further processing.

## Step 9 — Clean up

```bash
rm -f /tmp/scrape_output.html
agent-browser --profile ~/.claude/browser-profiles/<domain> close
```

Do NOT delete the profile directory — it persists for future use.

## Error Handling

- **agent-browser not installed**: Tell the user: `npm install -g agent-browser && agent-browser install`
- **`security` command not found (Linux)**: Skip Keychain steps, use env vars or prompt
- **Login fails**: Report the error, ask the user for guidance. Try `snapshot -i` to show what's visible
- **Empty HTML**: Try `agent-browser snapshot` to inspect the page state
- **Conversion fails**: Return the raw HTML from `/tmp/scrape_output.html`
- **Profile is stale (session expired)**: If a profile exists but the target page redirects to login, delete the profile and restart from Step 3:
  ```bash
  rm -rf ~/.claude/browser-profiles/<domain>
  ```

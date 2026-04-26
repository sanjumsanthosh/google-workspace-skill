# Google Workspace Skill

Reusable OpenClaw skill for Google Tasks and Gmail.

It uses only Python standard library code for Google API calls. OAuth is a one-time local browser consent flow that returns a refresh token, which is then reused through environment variables.

## What It Supports

- Google Tasks: list task lists, list tasks, create, update, move, complete, delete, clear completed.
- Gmail: search messages, read metadata, read decoded body text, list/create labels, add/remove labels, list threads.
- OpenClaw hook wrapper in `hooks/openclaw/handler.js`.

## Required Environment

Create `.env` from `.env.example`, or export these variables:

```bash
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REFRESH_TOKEN="your-refresh-token"
```

The helper scripts also load `.env` from the repo root automatically.

## One-Time OAuth Setup

Run:

```bash
python3 scripts/get_tokens.py
```

The script opens a Google consent URL, waits for a redirect on `http://localhost:8080`, exchanges the auth code for tokens, and prints the env vars to store.

Scopes requested:

- `https://www.googleapis.com/auth/tasks`
- `https://www.googleapis.com/auth/gmail.modify`

`gmail.modify` is used because this skill needs read/search plus label modification and message organization, without granting Gmail delete access.

If Google returns `403 access_denied` while the OAuth app is in testing mode, add your Gmail account under:

`Google Cloud Console -> APIs & Services -> OAuth consent screen -> Audience -> Test users`

If scopes change later, run the consent flow again and replace the old refresh token. Existing refresh tokens do not automatically gain newly-added scopes.

## Direct CLI Usage

```bash
python3 scripts/google_helper.py list_tasklists
python3 scripts/google_helper.py list_tasks
python3 scripts/google_helper.py create_task "Submit GST filing" "Due Friday"
python3 scripts/google_helper.py complete_task TASK_ID
python3 scripts/google_helper.py search_emails "is:unread" 10
python3 scripts/google_helper.py get_email MESSAGE_ID
python3 scripts/google_helper.py get_email_full MESSAGE_ID
python3 scripts/google_helper.py list_labels
python3 scripts/google_helper.py add_label MESSAGE_ID LABEL_ID
```

Run without args to print the available commands:

```bash
python3 scripts/google_helper.py
```

## Guardrails

- Do not delete tasks unless the user explicitly says delete.
- Gmail support is intentionally non-sending.
- Do not guess task IDs, message IDs, or label IDs. List/search first.
- API errors are returned with status code and response body; no silent retries.


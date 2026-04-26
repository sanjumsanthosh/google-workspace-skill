# Google Workspace MCP / OpenClaw Skill

`google-workspace` is a small, dependency-free OpenClaw skill for working with
Google Tasks and Gmail from an agent environment.

It is designed to be easy to copy into an OpenClaw skills workspace, easy to
update as a normal Git repo, and safe enough to reuse without storing secrets in
source control.

## Features

- Google Tasks
  - list task lists
  - list pending tasks
  - create tasks
  - update task title/notes
  - move tasks
  - complete tasks
  - delete tasks
  - clear completed tasks
- Gmail
  - search messages with Gmail query syntax
  - fetch message metadata and snippets
  - fetch decoded plain-text message bodies
  - list labels
  - create labels
  - add/remove labels from messages
  - list threads
- OpenClaw integration
  - keyword hook metadata
  - JavaScript handler for calling the Python helper
  - repo-local `.env` loading

The Python code uses only the standard library.

## Repository Layout

```text
google-workspace
├── README.md
├── SKILL.md
├── _meta.json
├── assets
│   └── .gitkeep
├── hooks
│   └── openclaw
│       ├── HOOK.md
│       └── handler.js
├── references
│   └── openclaw-integration.md
└── scripts
    ├── get_tokens.py
    └── google_helper.py
```

## Requirements

- Python 3
- Node.js if you use the OpenClaw hook handler
- A Google Cloud OAuth client ID and client secret
- Google Tasks API enabled in the Google Cloud project
- Gmail API enabled in the Google Cloud project

## Install

Clone this repo wherever you keep reusable skills:

```bash
git clone https://github.com/sanjumsanthosh/google-workspace-mcp.git
cd google-workspace-mcp
```

For OpenClaw, copy or symlink the repo into your skills workspace:

```bash
ln -s "$PWD" /home/opc/.openclaw/workspace/skills/google-workspace
```

If you prefer copying:

```bash
cp -R "$PWD" /home/opc/.openclaw/workspace/skills/google-workspace
```

## Configure Environment

Create a local `.env` file:

```bash
cp .env.example .env
```

Fill in:

```bash
GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-client-secret"
GOOGLE_REFRESH_TOKEN="generated-refresh-token"
```

The scripts load `.env` from the repo root automatically. You can also export
the variables in your shell instead.

Do not commit `.env`. It is ignored by Git.

## One-Time OAuth Flow

Use the included script to generate a refresh token:

```bash
python3 scripts/get_tokens.py
```

The script:

1. builds the Google OAuth authorization URL
2. opens the consent page in your browser
3. waits for the redirect on `http://localhost:8080`
4. exchanges the auth code for an access token and refresh token
5. prints the environment variables to store in `.env`

Requested scopes:

```text
https://www.googleapis.com/auth/tasks
https://www.googleapis.com/auth/gmail.modify
```

`gmail.modify` is intentional. It allows read/search plus label and message
organization operations without granting Gmail delete access.

## Google OAuth Test User Fix

If the OAuth consent screen is still in testing mode and Google returns
`403 access_denied`, add the Gmail account as a test user:

```text
Google Cloud Console
-> APIs & Services
-> OAuth consent screen
-> Audience
-> Test users
-> Add users
```

Then rerun:

```bash
python3 scripts/get_tokens.py
```

If you change scopes later, run the consent flow again and replace the old
refresh token. A refresh token minted before a scope change does not
automatically gain the new scope.

## CLI Usage

Run without arguments to see all commands:

```bash
python3 scripts/google_helper.py
```

### Google Tasks

List task lists:

```bash
python3 scripts/google_helper.py list_tasklists
```

List pending tasks:

```bash
python3 scripts/google_helper.py list_tasks
python3 scripts/google_helper.py list_tasks <tasklist_id>
```

Create a task:

```bash
python3 scripts/google_helper.py create_task "Submit GST filing" "Due Friday"
```

Create a task with a due date:

```bash
python3 scripts/google_helper.py create_task "Submit GST filing" "Due Friday" "2026-04-30T00:00:00.000Z"
```

Complete a task:

```bash
python3 scripts/google_helper.py complete_task <task_id>
```

Update a task:

```bash
python3 scripts/google_helper.py update_task <task_id> "New title" "New notes"
```

Move a task:

```bash
python3 scripts/google_helper.py move_task <task_id>
python3 scripts/google_helper.py move_task <task_id> @default <parent_id> <previous_id>
```

Delete a task:

```bash
python3 scripts/google_helper.py delete_task <task_id>
```

Clear completed tasks:

```bash
python3 scripts/google_helper.py clear_completed
```

### Gmail

Search emails:

```bash
python3 scripts/google_helper.py search_emails "is:unread" 10
python3 scripts/google_helper.py search_emails "from:someone@example.com" 5
python3 scripts/google_helper.py search_emails "subject:invoice has:attachment"
```

Get message metadata and snippet:

```bash
python3 scripts/google_helper.py get_email <message_id>
```

Get message metadata plus decoded body:

```bash
python3 scripts/google_helper.py get_email_full <message_id>
```

List labels:

```bash
python3 scripts/google_helper.py list_labels
```

Create a label:

```bash
python3 scripts/google_helper.py create_label "FollowUp"
```

Add or remove a label:

```bash
python3 scripts/google_helper.py add_label <message_id> <label_id>
python3 scripts/google_helper.py remove_label <message_id> <label_id>
```

List threads:

```bash
python3 scripts/google_helper.py list_threads "is:unread" 10
```

## Gmail Query Examples

| Query | Meaning |
| --- | --- |
| `is:unread` | Unread messages |
| `from:name@example.com` | Messages from a sender |
| `subject:invoice` | Messages with subject keyword |
| `after:2026/04/01` | Messages after a date |
| `has:attachment` | Messages with attachments |
| `label:FollowUp` | Messages with a label |
| `is:starred` | Starred messages |

## OpenClaw Hook

The OpenClaw hook lives in:

```text
hooks/openclaw/handler.js
```

It expects an input object shaped like:

```json
{
  "command": "search_emails",
  "args": ["is:unread", "10"]
}
```

The handler calls:

```bash
python3 scripts/google_helper.py <command> <args...>
```

and returns the parsed JSON response.

## Guardrails

- Do not delete tasks unless the user explicitly asks to delete.
- This skill does not send email.
- Do not guess task IDs, message IDs, thread IDs, or label IDs.
- List/search first when an ID is unknown.
- API errors include the HTTP status and response body.
- The helper does not silently retry failed Google API calls.

## Troubleshooting

### Missing env vars

Set:

```text
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REFRESH_TOKEN
```

### 401 Unauthorized

The refresh token may be revoked or invalid. Rerun:

```bash
python3 scripts/get_tokens.py
```

### 403 Forbidden or access_denied

Check:

- the Gmail account is listed under OAuth consent screen test users
- the Google Tasks API is enabled
- the Gmail API is enabled
- the refresh token was minted with the current scopes

### No refresh token returned

Revoke the app from:

```text
https://myaccount.google.com/permissions
```

Then rerun the OAuth script. The script uses `prompt=consent` and
`access_type=offline`, but Google may still skip issuing a new refresh token
until the old app grant is revoked.

## Security Notes

- Never commit `.env`.
- Never commit `GOOGLE_REFRESH_TOKEN`.
- Treat the refresh token like a password.
- Prefer a dedicated Google OAuth client for this skill.
- If a token leaks, revoke the app grant from your Google account immediately.

## License

No license has been added yet. Add one before accepting external contributions.

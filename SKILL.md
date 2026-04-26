---
name: google-workspace
description: "Manage Google Tasks and Gmail: list/create/move/complete tasks, read/search emails, manage labels."
metadata:
  openclaw:
    requires:
      bins:
        - python3
      env:
        - GOOGLE_CLIENT_ID
        - GOOGLE_CLIENT_SECRET
        - GOOGLE_REFRESH_TOKEN
      os:
        - linux
        - darwin
---

# Google Workspace Skill

A minimal, self-contained skill to manage Google Tasks and Gmail using Google REST APIs. No Python dependencies are required.

## Setup Required

Set these env vars, either in shell or in a repo-local `.env` file:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`

Generate the refresh token with:

```bash
python3 scripts/get_tokens.py
```

All API calls go through:

```bash
python3 scripts/google_helper.py <command> [args...]
```

## Tasks

List all task lists:

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
python3 scripts/google_helper.py create_task "Task title" "Optional notes"
```

Create a task with a due date:

```bash
python3 scripts/google_helper.py create_task "Task title" "Optional notes" "2026-04-25T00:00:00.000Z"
```

Complete a task:

```bash
python3 scripts/google_helper.py complete_task <task_id>
```

Move a task:

```bash
python3 scripts/google_helper.py move_task <task_id>
python3 scripts/google_helper.py move_task <task_id> @default <parent_id> <previous_id>
```

Update title or notes:

```bash
python3 scripts/google_helper.py update_task <task_id> "New title" "New notes"
```

Delete a task:

```bash
python3 scripts/google_helper.py delete_task <task_id>
```

Clear completed tasks:

```bash
python3 scripts/google_helper.py clear_completed
```

## Gmail

Search emails:

```bash
python3 scripts/google_helper.py search_emails "is:unread"
python3 scripts/google_helper.py search_emails "from:someone@gmail.com" 5
python3 scripts/google_helper.py search_emails "subject:invoice has:attachment"
```

Get email metadata:

```bash
python3 scripts/google_helper.py get_email <message_id>
```

Get email metadata plus decoded body:

```bash
python3 scripts/google_helper.py get_email_full <message_id>
```

List labels:

```bash
python3 scripts/google_helper.py list_labels
```

Create a label:

```bash
python3 scripts/google_helper.py create_label "MyLabel"
```

Add or remove a label:

```bash
python3 scripts/google_helper.py add_label <message_id> <label_id>
python3 scripts/google_helper.py remove_label <message_id> <label_id>
```

List threads:

```bash
python3 scripts/google_helper.py list_threads "is:unread"
```

## Gmail Query Reference

| Query | Meaning |
|---|---|
| `is:unread` | All unread emails |
| `from:x@y.com` | From specific sender |
| `subject:invoice` | By subject keyword |
| `after:2026/04/01` | After a date |
| `has:attachment` | Has attachments |
| `label:MyLabel` | By label |
| `is:starred` | Starred emails |

## Guardrails

- Never delete tasks unless the user explicitly says "delete".
- Never send emails; this skill does not implement mail sending.
- If a `task_id`, `message_id`, or `label_id` is unknown, list/search first.
- If env vars are missing, report the exact missing names.
- If an API returns an error, show the status code and response body.
- Do not guess or invent IDs.

## Error Handling

- Missing env vars: set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN`.
- 401 Unauthorized: refresh token may be revoked; re-run `scripts/get_tokens.py`.
- 403 Forbidden: check test users and scopes. Required scopes are `tasks` and `gmail.modify`.
- 404 Not Found: ID is likely wrong; re-fetch with list/search first.

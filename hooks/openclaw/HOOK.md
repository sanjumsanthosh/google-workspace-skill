---
name: google-workspace
trigger: keyword
keywords: ["task", "tasks", "gmail", "email", "inbox", "label", "mail", "google"]
---

# Google Workspace Hook

## Trigger Conditions

- User mentions tasks, inbox, emails, labels, mail, or Google.
- User wants to create, list, move, complete, or search.

## On Trigger

1. Load environment variables from `.env` in the skill root.
2. Call `scripts/google_helper.py` with the right command.
3. Return formatted JSON output to the agent.

## Guardrails

- Never delete tasks unless user says "delete" explicitly.
- Never send emails.
- If env vars are missing, tell user exactly which ones are needed.


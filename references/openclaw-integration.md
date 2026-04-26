# OpenClaw Integration Reference

## Available Commands

### Tasks

| Command | Args | What it does |
|---|---|---|
| `list_tasklists` | none | Lists all task lists |
| `list_tasks` | `[tasklist_id]` | Lists pending tasks |
| `get_task` | `task_id [tasklist_id]` | Fetches one task |
| `create_task` | `title [notes] [due] [tasklist_id]` | Creates a task |
| `complete_task` | `task_id [tasklist_id]` | Marks a task complete |
| `update_task` | `task_id [title] [notes] [tasklist_id]` | Updates title/notes |
| `move_task` | `task_id [tasklist_id] [parent] [previous]` | Moves task position |
| `delete_task` | `task_id [tasklist_id]` | Permanently deletes task |
| `clear_completed` | `[tasklist_id]` | Clears completed tasks |

### Gmail

| Command | Args | What it does |
|---|---|---|
| `search_emails` | `query [max]` | Searches emails |
| `get_email` | `msg_id` | Gets metadata and snippet |
| `get_email_full` | `msg_id` | Gets metadata and decoded body |
| `list_labels` | none | Lists labels |
| `create_label` | `name` | Creates a label |
| `add_label` | `msg_id label_id` | Adds a label |
| `remove_label` | `msg_id label_id` | Removes a label |
| `list_threads` | `[query] [max]` | Lists threads |

## Gmail Query Examples

- `is:unread`: all unread emails
- `from:boss@company.com`: from a specific sender
- `subject:invoice`: subject match
- `after:2026/04/01`: after a date
- `has:attachment`: emails with attachments
- `label:MyLabel`: emails with a label


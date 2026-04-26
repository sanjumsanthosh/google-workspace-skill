#!/usr/bin/env python3
import base64
import html
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


TASKS_API = "https://tasks.googleapis.com/tasks/v1"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


def load_dotenv():
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def die(payload, status=0):
    print(json.dumps(payload, indent=2))
    sys.exit(status)


def error_payload(kind, message, *, status=None, body=None, operation=None, details=None):
    payload = {
        "ok": False,
        "error": {
            "type": kind,
            "message": message,
        },
    }
    if status is not None:
        payload["error"]["status"] = status
    if body is not None:
        payload["error"]["body"] = body
    if operation is not None:
        payload["error"]["operation"] = operation
    if details is not None:
        payload["error"]["details"] = details
    return payload


def path_id(value):
    return urllib.parse.quote(str(value), safe="@")


def get_token():
    load_dotenv()
    required = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        die(
            error_payload(
                "missing_env",
                "Google Workspace credentials are not fully configured.",
                operation="refresh_access_token",
                details={"missing": missing},
            )
        )

    data = urllib.parse.urlencode(
        {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        }
    ).encode()

    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    try:
        resp = json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        die(token_error_payload(exc.code, parse_error_body(body)))
    except urllib.error.URLError as exc:
        die(
            error_payload(
                "oauth_network_error",
                "Could not reach Google's OAuth token endpoint.",
                operation="refresh_access_token",
                details={"reason": str(exc.reason)},
            )
        )

    if "access_token" not in resp:
        die(
            error_payload(
                "oauth_token_response_missing_access_token",
                "Google returned a token response without an access_token.",
                operation="refresh_access_token",
                body=resp,
            )
        )
    return resp["access_token"]


def parse_error_body(body):
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body


def body_error_code(body):
    if isinstance(body, dict):
        value = body.get("error")
        if isinstance(value, dict):
            return value.get("status") or value.get("message")
        return value
    return None


def token_error_payload(status, body):
    code = body_error_code(body)
    if code == "invalid_grant":
        return error_payload(
            "oauth_refresh_token_invalid",
            "Google rejected the refresh token. It is expired, revoked, was minted for a different OAuth client, or was invalidated after scope/client changes.",
            status=status,
            body=body,
            operation="refresh_access_token",
        )
    if code == "invalid_client":
        return error_payload(
            "oauth_client_invalid",
            "Google rejected the OAuth client credentials.",
            status=status,
            body=body,
            operation="refresh_access_token",
        )
    return error_payload(
        "oauth_refresh_failed",
        "Google OAuth token refresh failed.",
        status=status,
        body=body,
        operation="refresh_access_token",
    )


def api_error_payload(status, body, method, url):
    code = body_error_code(body)
    if status == 401:
        return error_payload(
            "google_api_unauthorized",
            "Google API rejected the access token.",
            status=status,
            body=body,
            operation=f"{method} {url}",
        )
    if status == 403:
        return error_payload(
            "google_api_forbidden",
            "Google API denied this request. This is usually a scope, API enablement, or OAuth test-user issue.",
            status=status,
            body=body,
            operation=f"{method} {url}",
            details={"google_error": code},
        )
    if status == 404:
        return error_payload(
            "google_api_not_found",
            "Google API could not find the requested resource.",
            status=status,
            body=body,
            operation=f"{method} {url}",
        )
    return error_payload(
        "google_api_request_failed",
        "Google API request failed.",
        status=status,
        body=body,
        operation=f"{method} {url}",
    )


def api(method, url, body=None):
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        resp = urllib.request.urlopen(req)
        raw = resp.read()
        return json.loads(raw) if raw else {"status": "ok"}
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        die(api_error_payload(exc.code, parse_error_body(body_text), method, url))
    except urllib.error.URLError as exc:
        die(
            error_payload(
                "google_api_network_error",
                "Could not reach the Google API endpoint.",
                operation=f"{method} {url}",
                details={"reason": str(exc.reason)},
            )
        )


NOISE_LINE_PATTERNS = [
    r"^read more$",
    r"^view job:?$",
    r"^view more posts$",
    r"^view the .+ policy",
    r"^see all jobs on linkedin:?$",
    r"^job search smarter with premium$",
    r"^apply with resume & profile$",
    r"^this company is actively hiring$",
    r"^manage your .+:?$",
    r"^unsubscribe(?:\s*:.*)?$",
    r"^unsubscribe from .+",
    r"^help:?$",
    r"^learn why we included this:?$",
    r"^learn more$",
    r"^please do not reply to this message\.?$",
    r"^you are receiving .+ emails?\.?$",
    r"^you are receiving this email because .+",
    r"^this email was intended for .+",
    r"^to stop receiving these emails, .+",
    r"^forwarding this invitation could allow .+",
    r"^invitation from google calendar:?$",
    r"^hide .+",
    r"^img$",
    r"^© .+",
    r"^\(c\) .+",
    r"^all rights reserved\.?$",
    r"^linkedin and the linkedin logo are registered trademarks .+",
    r"^san francisco, ca .+",
    r"^\d\s+\d\s+\d\s+.+",
    r"^\d+\s+upvotes?$",
    r"^\d+\s+comments?$",
    r"^\d+\s+(company|school)\s+alumni$",
    r"^\d+\s+connections?$",
]


def normalize_text(text):
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(
        r"[\u0000-\u0008\u000b\u000c\u000e-\u001f"
        r"\u00ad"
        r"\u034f"
        r"\u200b-\u200f"
        r"\u2028\u2029"
        r"\u202a-\u202e"
        r"\ufeff]",
        " ",
        text,
    )
    text = text.replace("\u00a0", " ")
    text = text.replace("\u2026", "...")
    text = re.sub(r"\b1zwnj000\b", "1000", text)
    text = re.sub(r"\s+100%\s+secure transactions.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+©\s+cred\.club.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text


def is_noise_line(line):
    lowered = line.strip().lower()
    return any(re.search(pattern, lowered) for pattern in NOISE_LINE_PATTERNS)


def clean_body(text):
    text = normalize_text(text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = [line.strip() for line in text.splitlines()]
    seen = set()
    cleaned = []
    for line in lines:
        line = re.sub(r"\bimg\b", "", line).strip()
        key = line.lower()
        if (
            line
            and not re.fullmatch(r"[•·&;|\-_=\s\d]+", line)
            and not re.fullmatch(r"\d+", line)
            and len(line) > 1
            and not is_noise_line(line)
            and key not in seen
        ):
            cleaned.append(line)
            seen.add(key)

    return "\n".join(cleaned).strip()


def clean_snippet(text):
    text = normalize_text(text)
    text = re.sub(r"\bimg\b", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_header_value(text):
    text = html.unescape(text)
    text = re.sub(
        r"[\u0000-\u0008\u000b\u000c\u000e-\u001f"
        r"\u00ad"
        r"\u034f"
        r"\u200b-\u200f"
        r"\u2028\u2029"
        r"\u202a-\u202e"
        r"\ufeff]",
        " ",
        text,
    )
    text = text.replace("\u00a0", " ")
    text = text.replace("\u2026", "...")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_headers(headers):
    return {key: clean_header_value(value) for key, value in headers.items()}


def decode_base64(data):
    if not data:
        return ""
    padding = "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(data + padding).decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_body(payload):
    mime = payload.get("mimeType", "")

    if mime == "text/plain":
        return clean_body(decode_base64(payload.get("body", {}).get("data", "")))

    if mime == "text/html":
        return clean_body(decode_base64(payload.get("body", {}).get("data", "")))

    plain = ""
    html_fallback = ""
    for part in payload.get("parts", []):
        sub_mime = part.get("mimeType", "")
        result = extract_body(part)
        if sub_mime == "text/plain" and result:
            plain = result
        elif sub_mime == "text/html" and result:
            html_fallback = result
        elif result and not plain:
            plain = result

    return plain or html_fallback


def parse_headers(headers):
    keys = {"From", "To", "Subject", "Date", "CC", "Reply-To"}
    return {header["name"]: header["value"] for header in headers if header.get("name") in keys}


def query(params):
    return urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})


def list_tasklists():
    return api("GET", f"{TASKS_API}/users/@me/lists")


def list_tasks(tasklist="@default"):
    qs = query({"showCompleted": "false", "showHidden": "false"})
    return api("GET", f"{TASKS_API}/lists/{path_id(tasklist)}/tasks?{qs}")


def get_task(task_id, tasklist="@default"):
    return api("GET", f"{TASKS_API}/lists/{path_id(tasklist)}/tasks/{path_id(task_id)}")


def create_task(title, notes="", due=None, tasklist="@default"):
    body = {"title": title, "notes": notes, "status": "needsAction"}
    if due:
        body["due"] = due
    return api("POST", f"{TASKS_API}/lists/{path_id(tasklist)}/tasks", body)


def complete_task(task_id, tasklist="@default"):
    task = get_task(task_id, tasklist)
    task["status"] = "completed"
    return api("PUT", f"{TASKS_API}/lists/{path_id(tasklist)}/tasks/{path_id(task_id)}", task)


def update_task(task_id, title=None, notes=None, tasklist="@default"):
    task = get_task(task_id, tasklist)
    if title:
        task["title"] = title
    if notes:
        task["notes"] = notes
    return api("PUT", f"{TASKS_API}/lists/{path_id(tasklist)}/tasks/{path_id(task_id)}", task)


def move_task(task_id, tasklist="@default", parent=None, previous=None):
    qs = query({"parent": parent, "previous": previous})
    suffix = f"?{qs}" if qs else ""
    return api("POST", f"{TASKS_API}/lists/{path_id(tasklist)}/tasks/{path_id(task_id)}/move{suffix}")


def delete_task(task_id, tasklist="@default"):
    api("DELETE", f"{TASKS_API}/lists/{path_id(tasklist)}/tasks/{path_id(task_id)}")
    return {"status": "deleted", "task_id": task_id}


def clear_completed(tasklist="@default"):
    return api("POST", f"{TASKS_API}/lists/{path_id(tasklist)}/clear")


def search_emails(search_query, max_results=10):
    qs = query({"q": search_query, "maxResults": max_results})
    return api("GET", f"{GMAIL_API}/messages?{qs}")


def get_email_meta(msg_id):
    msg = api("GET", f"{GMAIL_API}/messages/{path_id(msg_id)}?format=metadata")
    headers = clean_headers(parse_headers(msg.get("payload", {}).get("headers", [])))
    return {
        "id": msg["id"],
        "threadId": msg["threadId"],
        "labelIds": msg.get("labelIds", []),
        "snippet": clean_snippet(msg.get("snippet", "")),
        "headers": headers,
        "sizeEstimate": msg.get("sizeEstimate"),
    }


def get_email_full(msg_id):
    msg = api("GET", f"{GMAIL_API}/messages/{path_id(msg_id)}?format=full")
    payload = msg.get("payload", {})
    return {
        "id": msg["id"],
        "threadId": msg["threadId"],
        "labelIds": msg.get("labelIds", []),
        "snippet": clean_snippet(msg.get("snippet", "")),
        "headers": clean_headers(parse_headers(payload.get("headers", []))),
        "body": extract_body(payload),
        "sizeEstimate": msg.get("sizeEstimate"),
    }


def list_labels():
    return api("GET", f"{GMAIL_API}/labels")


def create_label(name):
    return api("POST", f"{GMAIL_API}/labels", {"name": name})


def add_label(msg_id, label_id):
    return api("POST", f"{GMAIL_API}/messages/{path_id(msg_id)}/modify", {"addLabelIds": [label_id]})


def remove_label(msg_id, label_id):
    return api("POST", f"{GMAIL_API}/messages/{path_id(msg_id)}/modify", {"removeLabelIds": [label_id]})


def list_threads(search_query="", max_results=10):
    qs = query({"q": search_query, "maxResults": max_results})
    return api("GET", f"{GMAIL_API}/threads?{qs}")


def require_args(args, count, usage):
    if len(args) < count:
        die({"error": "Missing required arguments", "usage": usage})


def dispatch(cmd, args):
    if cmd == "list_tasklists":
        return list_tasklists()
    if cmd == "list_tasks":
        return list_tasks(args[0] if args else "@default")
    if cmd == "get_task":
        require_args(args, 1, "get_task <task_id> [tasklist_id]")
        return get_task(args[0], args[1] if len(args) > 1 else "@default")
    if cmd == "create_task":
        require_args(args, 1, "create_task <title> [notes] [due] [tasklist_id]")
        return create_task(
            args[0],
            args[1] if len(args) > 1 else "",
            args[2] if len(args) > 2 else None,
            args[3] if len(args) > 3 else "@default",
        )
    if cmd == "complete_task":
        require_args(args, 1, "complete_task <task_id> [tasklist_id]")
        return complete_task(args[0], args[1] if len(args) > 1 else "@default")
    if cmd == "update_task":
        require_args(args, 1, "update_task <task_id> [title] [notes] [tasklist_id]")
        return update_task(
            args[0],
            args[1] if len(args) > 1 else None,
            args[2] if len(args) > 2 else None,
            args[3] if len(args) > 3 else "@default",
        )
    if cmd == "move_task":
        require_args(args, 1, "move_task <task_id> [tasklist_id] [parent] [previous]")
        return move_task(
            args[0],
            args[1] if len(args) > 1 else "@default",
            args[2] if len(args) > 2 else None,
            args[3] if len(args) > 3 else None,
        )
    if cmd == "delete_task":
        require_args(args, 1, "delete_task <task_id> [tasklist_id]")
        return delete_task(args[0], args[1] if len(args) > 1 else "@default")
    if cmd == "clear_completed":
        return clear_completed(args[0] if args else "@default")
    if cmd == "search_emails":
        require_args(args, 1, "search_emails <query> [max_results]")
        return search_emails(args[0], int(args[1]) if len(args) > 1 else 10)
    if cmd == "get_email":
        require_args(args, 1, "get_email <message_id>")
        return get_email_meta(args[0])
    if cmd == "get_email_full":
        require_args(args, 1, "get_email_full <message_id>")
        return get_email_full(args[0])
    if cmd == "list_labels":
        return list_labels()
    if cmd == "create_label":
        require_args(args, 1, "create_label <name>")
        return create_label(args[0])
    if cmd == "add_label":
        require_args(args, 2, "add_label <message_id> <label_id>")
        return add_label(args[0], args[1])
    if cmd == "remove_label":
        require_args(args, 2, "remove_label <message_id> <label_id>")
        return remove_label(args[0], args[1])
    if cmd == "list_threads":
        return list_threads(args[0] if args else "", int(args[1]) if len(args) > 1 else 10)

    die({"available_commands": COMMANDS})


COMMANDS = [
    "list_tasklists",
    "list_tasks",
    "get_task",
    "create_task",
    "complete_task",
    "update_task",
    "move_task",
    "delete_task",
    "clear_completed",
    "search_emails",
    "get_email",
    "get_email_full",
    "list_labels",
    "create_label",
    "add_label",
    "remove_label",
    "list_threads",
]


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else None
    if not command:
        die({"available_commands": COMMANDS}, status=0)
    print(json.dumps(dispatch(command, sys.argv[2:]), indent=2, ensure_ascii=False))

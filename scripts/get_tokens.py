#!/usr/bin/env python3
"""One-time OAuth flow to get a Google refresh token.

Run:
    python3 scripts/get_tokens.py

Requires:
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

REDIRECT_URI = "http://localhost:8080"
SCOPES = [
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/gmail.modify",
]


def load_dotenv():
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def require_env(name):
    value = os.environ.get(name)
    if not value:
        print(f"Missing env var: {name}", file=sys.stderr)
        sys.exit(1)
    return value


class OAuthHandler(BaseHTTPRequestHandler):
    auth_code = None
    auth_error = None

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        OAuthHandler.auth_code = params.get("code", [None])[0]
        OAuthHandler.auth_error = params.get("error", [None])[0]

        self.send_response(200)
        self.end_headers()
        if OAuthHandler.auth_code:
            self.wfile.write(b"<h2>Done. You can close this tab.</h2>")
        else:
            self.wfile.write(b"<h2>OAuth failed. Check the terminal.</h2>")

    def log_message(self, *_args):
        pass


def main():
    load_dotenv()
    client_id = require_env("GOOGLE_CLIENT_ID")
    client_secret = require_env("GOOGLE_CLIENT_SECRET")

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
        }
    )

    print(f"\nOpening browser for Google auth...\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("Waiting for Google to redirect to localhost:8080 ...")
    server = HTTPServer(("localhost", 8080), OAuthHandler)
    server.handle_request()

    if OAuthHandler.auth_error:
        print(f"OAuth error: {OAuthHandler.auth_error}", file=sys.stderr)
        print("If this is access_denied in testing mode, add your Gmail as a test user.", file=sys.stderr)
        sys.exit(1)

    if not OAuthHandler.auth_code:
        print("No auth code received. Try again.", file=sys.stderr)
        sys.exit(1)

    token_data = urllib.parse.urlencode(
        {
            "code": OAuthHandler.auth_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=token_data,
        method="POST",
    )

    try:
        response = json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Token exchange failed with HTTP {exc.code}: {body}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 50)
    print("SUCCESS - add these to your .env or shell profile:")
    print("=" * 50)
    print(f'\nGOOGLE_CLIENT_ID="{client_id}"')
    print(f'GOOGLE_CLIENT_SECRET="{client_secret}"')
    print(f'GOOGLE_REFRESH_TOKEN="{response.get("refresh_token", "NOT_RETURNED")}"')
    print("\n" + "=" * 50)

    if "refresh_token" not in response:
        print("\nNo refresh_token returned.")
        print("Fix: revoke this app at https://myaccount.google.com/permissions, then re-run.")


if __name__ == "__main__":
    main()


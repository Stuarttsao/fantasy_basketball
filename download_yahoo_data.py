#!/usr/bin/env python3
"""Download raw data for the SAS 2025-26 Yahoo fantasy basketball league."""

from __future__ import annotations

import base64
import getpass
import hashlib
import http.server
import json
import os
import secrets
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional, Tuple


CLIENT_ID = (
    "dj0yJmk9WlBkemI3MGhWU05jJmQ9WVdrOVprRkNZVVYzVlcwbWNHbzlNQT09"
    "JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PTEy"
)
REDIRECT_URI = "https://127.0.0.1:8000/callback"
LEAGUE_ID = "95762"
LEAGUE_NAME = "SAS"
SEASON = "2025"

PROJECT_DIR = Path(__file__).resolve().parent
PRIVATE_DIR = PROJECT_DIR / ".local"
TOKEN_FILE = PRIVATE_DIR / "yahoo_tokens.json"
CERT_FILE = PRIVATE_DIR / "localhost.crt"
KEY_FILE = PRIVATE_DIR / "localhost.key"
OUTPUT_DIR = PROJECT_DIR / "data" / "raw" / "yahoo-2025-26"

AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
API_ROOT = "https://fantasysports.yahooapis.com/fantasy/v2"


def request_json(
    url: str,
    *,
    access_token: Optional[str] = None,
    data: Optional[dict[str, str]] = None,
    basic_auth: Optional[Tuple[str, str]] = None,
) -> dict:
    headers = {"Accept": "application/json"}
    body = None
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if basic_auth:
        encoded = base64.b64encode(f"{basic_auth[0]}:{basic_auth[1]}".encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    request = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise RuntimeError(f"Yahoo returned HTTP {error.code} for {url}\n{detail}") from error


def save_json(name: str, payload: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Saved {path.relative_to(PROJECT_DIR)}")


def load_tokens() -> Optional[dict]:
    if not TOKEN_FILE.exists():
        return None
    return json.loads(TOKEN_FILE.read_text())


def save_tokens(tokens: dict) -> None:
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    tokens["saved_at"] = int(time.time())
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2) + "\n")
    os.chmod(TOKEN_FILE, 0o600)


def client_secret() -> str:
    value = os.environ.get("YAHOO_CLIENT_SECRET")
    if value:
        return value
    if "--gui" in sys.argv:
        script = (
            'display dialog "Enter your Yahoo Client Secret" '
            'default answer "" with hidden answer '
            'buttons {"Cancel", "Continue"} default button "Continue"'
        )
        completed = subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )
        marker = "text returned:"
        if marker not in completed.stdout:
            return ""
        return completed.stdout.split(marker, 1)[1].strip()
    return getpass.getpass("Yahoo Client Secret (input hidden): ").strip()


def ensure_certificate() -> None:
    if CERT_FILE.exists() and KEY_FILE.exists():
        return
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating a local certificate for Yahoo's registered HTTPS callback...")
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(KEY_FILE),
            "-out",
            str(CERT_FILE),
            "-days",
            "365",
            "-subj",
            "/CN=127.0.0.1",
            "-addext",
            "subjectAltName=IP:127.0.0.1",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def authorize(secret: str) -> dict:
    ensure_certificate()
    state = secrets.token_urlsafe(24)
    query = urllib.parse.urlencode(
        {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "state": state,
        }
    )
    authorization_url = f"{AUTH_URL}?{query}"
    result: dict[str, str] = {}

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            code = params.get("code", [""])[0]
            callback_state = params.get("state", [""])[0]
            error = params.get("error", [""])[0]

            if error:
                result["error"] = error
                result["complete"] = "1"
                message = b"Yahoo authorization failed. You can return to the terminal."
                status = 400
            elif code and callback_state:
                result["code"] = code
                result["state"] = callback_state
                result["complete"] = "1"
                message = b"Yahoo authorization received. You can return to the terminal."
                status = 200
            else:
                message = b"Waiting for the Yahoo OAuth callback."
                status = 200

            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = http.server.HTTPServer(("127.0.0.1", 8000), CallbackHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT_FILE, KEY_FILE)
    server.socket = context.wrap_socket(server.socket, server_side=True)

    print("\nOpening Yahoo authorization in your browser.")
    print("Because the callback uses a local certificate, approve the browser warning once.")
    print(f"If the browser does not open, visit:\n{authorization_url}\n")
    webbrowser.open(authorization_url)
    while not result.get("complete"):
        server.handle_request()
    server.server_close()

    if result.get("error"):
        raise RuntimeError(f"Yahoo authorization failed: {result['error']}")
    if result.get("state") != state or not result.get("code"):
        raise RuntimeError("Invalid Yahoo OAuth callback.")

    tokens = request_json(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": result["code"],
        },
        basic_auth=(CLIENT_ID, secret),
    )
    save_tokens(tokens)
    return tokens


def access_token() -> str:
    tokens = load_tokens()
    if not tokens:
        secret = client_secret()
        return authorize(secret)["access_token"]

    expires_at = int(tokens.get("saved_at", 0)) + int(tokens.get("expires_in", 0))
    if time.time() < expires_at - 60:
        return tokens["access_token"]

    secret = client_secret()
    refreshed = request_json(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "redirect_uri": REDIRECT_URI,
            "refresh_token": tokens["refresh_token"],
        },
        basic_auth=(CLIENT_ID, secret),
    )
    if "refresh_token" not in refreshed:
        refreshed["refresh_token"] = tokens["refresh_token"]
    save_tokens(refreshed)
    return refreshed["access_token"]


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def unique_values(payload: dict, key: str) -> set[str]:
    return {
        str(item[key])
        for item in walk(payload)
        if isinstance(item, dict) and item.get(key) is not None
    }


def chunked(values: list[str], size: int):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def find_game_key(payload: dict) -> str:
    candidates = []

    def inspect(value) -> None:
        if isinstance(value, dict):
            if str(value.get("season", "")) == SEASON and value.get("game_key"):
                candidates.append(str(value["game_key"]))
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            merged = {}
            for child in value:
                if isinstance(child, dict):
                    merged.update(child)
            if str(merged.get("season", "")) == SEASON and merged.get("game_key"):
                candidates.append(str(merged["game_key"]))
            for child in value:
                inspect(child)

    inspect(payload)
    if not candidates:
        raise RuntimeError(f"Could not find Yahoo NBA game key for the {SEASON} season.")
    return candidates[0]


def api_get(path: str, token: str) -> dict:
    separator = "&" if "?" in path else "?"
    return request_json(f"{API_ROOT}/{path}{separator}format=json", access_token=token)


def main() -> int:
    token = access_token()
    games = api_get("users;use_login=1/games;game_codes=nba", token)
    save_json("00_games", games)

    game_key = find_game_key(games)
    league_key = f"{game_key}.l.{LEAGUE_ID}"
    print(f"\nTargeting {LEAGUE_NAME}: {league_key}")

    endpoints = {
        "01_league_metadata": f"league/{league_key}/metadata",
        "02_settings": f"league/{league_key}/settings",
        "03_teams": f"league/{league_key}/teams",
        "04_standings": f"league/{league_key}/standings",
        "05_draft_results": f"league/{league_key}/draftresults",
    }

    failures = []
    downloaded = {}
    for name, path in endpoints.items():
        try:
            downloaded[name] = api_get(path, token)
            save_json(name, downloaded[name])
        except Exception as error:
            failures.append((name, str(error)))
            print(f"Could not download {name}: {error}", file=sys.stderr)

    draft_player_keys = sorted(
        unique_values(downloaded.get("05_draft_results", {}), "player_key")
    )
    for batch_number, keys in enumerate(chunked(draft_player_keys, 25)):
        name = f"draft_players_{batch_number:02d}"
        try:
            save_json(
                name,
                api_get(
                    f"league/{league_key}/players;player_keys={','.join(keys)}",
                    token,
                ),
            )
        except Exception as error:
            failures.append((name, str(error)))
            print(f"Could not download {name}: {error}", file=sys.stderr)

    for week in range(1, 24):
        name = f"scoreboard_week_{week:02d}"
        try:
            save_json(name, api_get(f"league/{league_key}/scoreboard;week={week}", token))
        except Exception as error:
            failures.append((name, str(error)))
            print(f"Could not download {name}: {error}", file=sys.stderr)

    seen_transactions: set[str] = set()
    for start in range(0, 5000, 25):
        name = f"transactions_{start:04d}"
        try:
            page = api_get(
                f"league/{league_key}/transactions;start={start};count=25",
                token,
            )
            transaction_keys = unique_values(page, "transaction_key")
            new_keys = transaction_keys - seen_transactions
            if start and not new_keys:
                break
            save_json(name, page)
            seen_transactions.update(new_keys)
            if len(new_keys) < 25:
                break
        except Exception as error:
            failures.append((name, str(error)))
            print(f"Could not download {name}: {error}", file=sys.stderr)
            break

    manifest = {
        "league_id": LEAGUE_ID,
        "league_name": LEAGUE_NAME,
        "season": "2025-26",
        "game_key": game_key,
        "league_key": league_key,
        "downloaded_at": int(time.time()),
        "transaction_count": len(seen_transactions),
        "failures": [name for name, _ in failures],
        "manifest_sha256": hashlib.sha256(league_key.encode()).hexdigest(),
    }
    save_json("manifest", manifest)

    print(f"\nRaw data is in {OUTPUT_DIR}")
    if failures:
        print("\nSome endpoints were unavailable:")
        for name, error in failures:
            print(f"- {name}: {error.splitlines()[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

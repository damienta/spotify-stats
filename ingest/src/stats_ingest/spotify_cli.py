"""`spotify-login` and `fetch-recent`: try the Spotify API from your own machine.

The login token is saved to a git-ignored file under `data/`. In AWS the poller keeps tokens
in DynamoDB instead (Stage 1, item 5).
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv

from stats_ingest.api_listens import listen_from_api
from stats_ingest.spotify import (
    SpotifyClient,
    SpotifyConfig,
    SpotifyError,
    Tokens,
    authorize_url,
    exchange_code,
)

DEFAULT_TOKEN_FILE = Path("data/spotify_token.json")
LOGIN_TIMEOUT_S = 300
LOCAL_TZ = ZoneInfo("Europe/London")


def save_tokens(path: Path, tokens: Tokens) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tokens.to_dict()), encoding="utf-8")


def load_tokens(path: Path) -> Tokens:
    if not path.exists():
        raise SpotifyError(f"no token at {path}: run `uv run spotify-login` first")
    return Tokens(**json.loads(path.read_text(encoding="utf-8")))


def wait_for_callback(redirect_uri: str, timeout_s: float) -> dict[str, str]:
    """Serve the redirect URI once and return the query Spotify sends back."""
    target = urlparse(redirect_uri)
    received: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (http.server's naming)
            url = urlparse(self.path)
            if url.path != target.path:
                self.send_error(404)
                return
            received.update({k: v[0] for k, v in parse_qs(url.query).items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Logged in to spotify-stats. You can close this tab.")

        def log_message(self, *args: object) -> None:
            pass

    server = HTTPServer((target.hostname or "127.0.0.1", target.port or 80), Handler)
    server.timeout = 1
    stop = threading.Timer(timeout_s, lambda: received.setdefault("error", "timed out"))
    stop.start()
    try:
        while not received:
            server.handle_request()
    finally:
        stop.cancel()
        server.server_close()
    return received


def login(argv: list[str] | None = None) -> None:
    """`spotify-login`: approve the app in your browser and save the token locally."""
    parser = argparse.ArgumentParser(description=login.__doc__)
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE)
    args = parser.parse_args(argv)
    load_dotenv()
    config = SpotifyConfig.from_env()

    state = secrets.token_urlsafe(16)
    url = authorize_url(config, state)
    print("Opening Spotify in your browser. If it doesn't open, visit:")
    print(url)
    webbrowser.open(url)

    callback = wait_for_callback(config.redirect_uri, LOGIN_TIMEOUT_S)
    if "error" in callback:
        sys.exit(f"Login failed: {callback['error']}")
    if callback.get("state") != state:
        sys.exit("Login failed: the callback's state didn't match (possible forged request)")

    with httpx.Client(timeout=30) as http:
        tokens = exchange_code(http, config, callback["code"])
        save_tokens(args.token_file, tokens)
        me = SpotifyClient(http, config, tokens).me()
    print(f"Logged in as {me.get('display_name') or me['id']}. Token saved to {args.token_file}")


def fetch_recent(argv: list[str] | None = None) -> None:
    """`fetch-recent`: print your most recent plays (Spotify keeps the last 50)."""
    parser = argparse.ArgumentParser(description=fetch_recent.__doc__)
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE)
    parser.add_argument("--limit", type=int, default=20, help="how many to print")
    parser.add_argument("--out", type=Path, help="also write them as JSON Lines listens")
    args = parser.parse_args(argv)
    load_dotenv()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    config = SpotifyConfig.from_env()

    with httpx.Client(timeout=30) as http:
        client = SpotifyClient(
            http,
            config,
            load_tokens(args.token_file),
            on_refresh=lambda tokens: save_tokens(args.token_file, tokens),
        )
        user_id = client.me()["id"]
        listens = [listen_from_api(item, user_id) for item in client.recently_played()]

    print(f"{len(listens)} recent plays for {user_id}, newest first:")
    for li in reversed(listens[-args.limit :]):
        when = li.played_at.astimezone(LOCAL_TZ)
        label = f"{li.track_name} - {li.artist_name}"
        print(f"  {when:%a %d %b %H:%M}  {label[:60]}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as f:
            for li in listens:
                f.write(json.dumps(li.to_dict()) + "\n")
        print(f"Wrote {len(listens)} listens to {args.out}")

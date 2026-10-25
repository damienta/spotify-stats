"""Copy the Spotify app credentials from .env into SSM Parameter Store, and create the API's
session-signing secret the first time.

    uv run python scripts/put_secrets.py

Run after Terraform has created the parameters. Values are never printed.
"""

from __future__ import annotations

import os
import secrets
import sys

import boto3
from dotenv import load_dotenv

PREFIX = "/spotify-stats"
PLACEHOLDER = "set-by-scripts/put_secrets.py"
FROM_ENV = {
    "spotify_client_id": "SPOTIFY_CLIENT_ID",
    "spotify_client_secret": "SPOTIFY_CLIENT_SECRET",
}


def main() -> None:
    load_dotenv()
    ssm = boto3.client("ssm")
    for parameter, variable in FROM_ENV.items():
        value = os.environ.get(variable)
        if not value:
            sys.exit(f"{variable} is not set in .env")
        ssm.put_parameter(
            Name=f"{PREFIX}/{parameter}", Value=value, Type="SecureString", Overwrite=True
        )
        print(f"set {PREFIX}/{parameter}")

    # Generated, not copied: changing it logs everyone out, so it's only set once.
    name = f"{PREFIX}/session_secret"
    current = ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]
    if current == PLACEHOLDER:
        ssm.put_parameter(
            Name=name, Value=secrets.token_urlsafe(48), Type="SecureString", Overwrite=True
        )
        print(f"generated {name}")
    else:
        print(f"kept {name}")


if __name__ == "__main__":
    main()

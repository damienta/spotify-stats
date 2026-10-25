"""Copy the Spotify app credentials from .env into SSM Parameter Store.

    uv run python scripts/put_secrets.py

Run after Terraform has created the parameters. Values are never printed.
"""

from __future__ import annotations

import os
import sys

import boto3
from dotenv import load_dotenv

PREFIX = "/spotify-stats"
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


if __name__ == "__main__":
    main()

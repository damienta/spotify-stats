"""Build and deploy everything from your machine (CI can't reach this AWS account; ADR 0002).

    uv run python scripts/deploy.py          # build, plan, confirm, apply, check
    uv run python scripts/deploy.py --yes    # don't ask before applying

Needs Terraform on PATH and the spotify-stats AWS profile.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
LIVE = ROOT / "infra" / "live"
STATE_BUCKET = "spotify-stats-tfstate-479863043672"


def step(title: str) -> None:
    print(f"\n==> {title}", flush=True)


def run(*args: str, cwd: Path = ROOT, capture: bool = False) -> str:
    result = subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=capture)
    return result.stdout if capture else ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="apply without asking")
    args = parser.parse_args()
    os.environ.setdefault("AWS_PROFILE", "spotify-stats")
    if not shutil.which("terraform"):
        sys.exit("terraform isn't on PATH")

    step("Building Lambda packages")
    run(sys.executable, str(ROOT / "scripts" / "build_lambdas.py"))

    step("Planning")
    run("terraform", "init", "-input=false", f"-backend-config=bucket={STATE_BUCKET}", cwd=LIVE)
    plan = LIVE / "deploy.tfplan"
    run("terraform", "plan", "-input=false", f"-out={plan.name}", cwd=LIVE)
    summary = run("terraform", "show", "-no-color", plan.name, cwd=LIVE, capture=True)
    if "No changes." in summary:
        print("Nothing to deploy.")
        plan.unlink()
    else:
        if not args.yes and input("\nApply this plan? [y/N] ").strip().lower() != "y":
            plan.unlink()
            sys.exit("Not applied.")
        step("Applying")
        try:
            run("terraform", "apply", "-input=false", plan.name, cwd=LIVE)
        finally:
            plan.unlink(missing_ok=True)

    step("Syncing secrets")
    run(sys.executable, str(ROOT / "scripts" / "put_secrets.py"))

    step("Checking the API")
    api = run("terraform", "output", "-raw", "api_url", cwd=LIVE, capture=True).strip()
    health = httpx.get(f"{api}health", timeout=30)
    health.raise_for_status()
    print(f"{api}health -> {health.json()}")
    redirect = run(
        "terraform", "output", "-raw", "spotify_redirect_uri", cwd=LIVE, capture=True
    ).strip()
    print(f"\nDeployed. Spotify redirect URI (must be in the developer dashboard):\n  {redirect}")


if __name__ == "__main__":
    main()

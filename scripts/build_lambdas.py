"""Package each Lambda into build/lambda/<name>/, ready for Terraform to zip.

Dependencies are installed as Linux ARM64 wheels (Lambda runs on Graviton), so this works
from Windows or macOS too. boto3 is left out because the Lambda runtime already has it.

    uv run python scripts/build_lambdas.py            # all functions
    uv run python scripts/build_lambdas.py poller     # just one
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build" / "lambda"
PLATFORM = "aarch64-manylinux_2_28"
PYTHON = "3.12"

# function -> (workspace package whose dependencies it needs, source dirs to include)
FUNCTIONS = {
    "poller": ("stats-ingest", ["ingest/src/stats_ingest"]),
    "stats": ("stats-jobs", ["jobs/src/stats_jobs", "ingest/src/stats_ingest"]),
    "api": ("stats-api", ["api/src/stats_api", "ingest/src/stats_ingest"]),
}

# Provided by the Lambda Python runtime.
RUNTIME_PROVIDED = ("boto3", "botocore", "s3transfer", "jmespath")


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def build(name: str) -> Path:
    package, sources = FUNCTIONS[name]
    out = BUILD / name
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)

    requirements = BUILD / f"{name}-requirements.txt"
    run(
        "uv",
        "export",
        "--package",
        package,
        "--frozen",
        "--no-dev",
        "--no-hashes",
        "--no-emit-workspace",
        "--no-header",
        "--quiet",
        "--output-file",
        str(requirements),
    )
    run(
        "uv",
        "pip",
        "install",
        "--quiet",
        "--requirements",
        str(requirements),
        "--target",
        str(out),
        "--python-platform",
        PLATFORM,
        "--python-version",
        PYTHON,
        "--only-binary",
        ":all:",
    )
    for source in sources:
        shutil.copytree(ROOT / source, out / Path(source).name)

    for path in list(out.iterdir()):
        if path.name.split("-")[0].split(".")[0] in RUNTIME_PROVIDED:
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    for cache in out.rglob("__pycache__"):
        shutil.rmtree(cache)

    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"built {name}: {size / 1e6:,.1f} MB unzipped -> {out.relative_to(ROOT)}")
    return out


def main() -> None:
    names = sys.argv[1:] or list(FUNCTIONS)
    unknown = set(names) - FUNCTIONS.keys()
    if unknown:
        sys.exit(f"unknown function(s): {', '.join(sorted(unknown))}")
    for name in names:
        build(name)


if __name__ == "__main__":
    main()

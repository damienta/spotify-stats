"""`parse-export`: turn a Spotify export into a JSON Lines file of listens."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from stats_ingest.export import parse_export


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path, help="export zip or unzipped export folder")
    parser.add_argument("--user", required=True, help="user ID to stamp on every listen")
    parser.add_argument("--out", type=Path, default=Path("data/listens.jsonl"))
    args = parser.parse_args(argv)

    result = parse_export(args.export, args.user)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for listen in sorted(result.listens, key=lambda li: li.played_at):
            f.write(json.dumps(listen.to_dict()) + "\n")

    print(f"Wrote {len(result.listens):,} listens to {args.out}")
    for reason, count in sorted(result.skipped.items()):
        print(f"  skipped {count:,} ({reason})")


if __name__ == "__main__":
    main()

"""`local-stats`: print all-time totals and top artists from a listens file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stats_jobs.stats import connect, top_artists, totals


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("listens", type=Path, nargs="?", default=Path("data/listens.jsonl"))
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args(argv)
    # Artist names can hold characters the Windows console code page can't print.
    sys.stdout.reconfigure(errors="replace")

    con = connect(args.listens)
    t = totals(con)
    print(f"{t.hours:,.0f} hours listened ({t.hours / 24:,.1f} days)")
    print(f"{t.streams:,} streams of {t.tracks:,} tracks by {t.artists:,} artists")
    print(f"from {t.first_played[:10]} to {t.last_played[:10]}")
    print()
    print(f"Top {args.top} artists")
    for rank, a in enumerate(top_artists(con, args.top), start=1):
        print(f"{rank:>3}. {a.artist_name:<32} {a.streams:>7,} streams  {a.hours:>7,.1f} h")


if __name__ == "__main__":
    main()

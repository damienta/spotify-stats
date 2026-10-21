"""Command-line entry points for the stats jobs."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from stats_jobs.stats import connect, top_artists, totals, write_parquet
from stats_jobs.windows import by_name

DEFAULT_PARQUET = Path("data/listens.parquet")


def main(argv: list[str] | None = None) -> None:
    """`local-stats`: print all-time totals and top artists from a listens file."""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("listens", type=Path, nargs="?", default=DEFAULT_PARQUET)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument(
        "--window",
        default="all_time",
        help="4_weeks, 6_months, 12_months, all_time or year_YYYY (default: all_time)",
    )
    args = parser.parse_args(argv)
    # Artist names can hold characters the Windows console code page can't print.
    sys.stdout.reconfigure(errors="replace")

    con = connect(args.listens)
    window = by_name(args.window, now=datetime.now(UTC))
    t = totals(con, window)
    print(f"[{window.name}]")
    print(f"{t.hours:,.0f} hours listened ({t.hours / 24:,.1f} days)")
    print(f"{t.streams:,} streams of {t.tracks:,} tracks by {t.artists:,} artists")
    print(f"from {t.first_played[:10]} to {t.last_played[:10]}")
    print()
    print(f"Top {args.top} artists")
    for rank, a in enumerate(top_artists(con, args.top, window), start=1):
        print(f"{rank:>3}. {a.artist_name:<32} {a.streams:>7,} streams  {a.hours:>7,.1f} h")


def convert(argv: list[str] | None = None) -> None:
    """`convert-listens`: deduplicate a JSON Lines listens file into Parquet."""
    parser = argparse.ArgumentParser(description=convert.__doc__)
    parser.add_argument("source", type=Path, nargs="?", default=Path("data/listens.jsonl"))
    parser.add_argument("dest", type=Path, nargs="?", default=DEFAULT_PARQUET)
    args = parser.parse_args(argv)

    rows = write_parquet(connect(args.source), args.dest)
    before, after = args.source.stat().st_size, args.dest.stat().st_size
    print(f"Wrote {rows:,} listens to {args.dest}")
    print(f"  {before / 1e6:,.1f} MB -> {after / 1e6:,.1f} MB ({before / after:,.1f}x smaller)")


if __name__ == "__main__":
    main()

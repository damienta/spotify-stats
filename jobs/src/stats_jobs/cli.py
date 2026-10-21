"""Command-line entry points for the stats jobs."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from stats_jobs.stats import connect, top, totals, write_parquet
from stats_jobs.windows import by_name

DEFAULT_PARQUET = Path("data/listens.parquet")


def main(argv: list[str] | None = None) -> None:
    """`local-stats`: print totals and top artists, tracks and albums for a time window."""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("listens", type=Path, nargs="?", default=DEFAULT_PARQUET)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument(
        "--window",
        default="all_time",
        help="4_weeks, 6_months, 12_months, all_time or year_YYYY (default: all_time)",
    )
    args = parser.parse_args(argv)
    # Names hold characters (curly quotes, other scripts) the Windows code page can't encode.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    con = connect(args.listens)
    window = by_name(args.window, now=datetime.now(UTC))
    t = totals(con, window)
    print(f"[{window.name}]")
    print(f"{t.hours:,.0f} hours listened ({t.hours / 24:,.1f} days)")
    print(f"{t.streams:,} streams of {t.tracks:,} tracks by {t.artists:,} artists")
    print(f"from {t.first_played[:10]} to {t.last_played[:10]}")
    for kind in ("artist", "track", "album"):
        print()
        print(f"Top {args.top} {kind}s")
        for rank, row in enumerate(top(con, kind, args.top, window), start=1):
            label = row.name if row.artist_name is None else f"{row.name} - {row.artist_name}"
            print(f"{rank:>3}. {label[:48]:<48} {row.streams:>7,} streams  {row.hours:>6,.1f} h")


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

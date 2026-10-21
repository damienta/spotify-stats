"""Command-line entry points for the stats jobs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from duckdb import DuckDBPyConnection

from stats_jobs.behaviour import discoveries, most_skipped, on_repeat, skip_rate
from stats_jobs.documents import build_documents, wrapped
from stats_jobs.habits import listening_clock, minutes_by, streaks
from stats_jobs.stats import connect, top, totals, write_parquet
from stats_jobs.windows import LOCAL_TZ, Window, by_name

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
    parser.add_argument("--wrapped", type=int, metavar="YEAR", help="print a Wrapped for YEAR")
    args = parser.parse_args(argv)
    # Names hold characters (curly quotes, other scripts) the Windows code page can't encode.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    con = connect(args.listens)
    if args.wrapped:
        print_wrapped(con, args.wrapped)
        return
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
    print_habits(con, window)
    print_behaviour(con, window)


WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def print_habits(con: DuckDBPyConnection, window: Window) -> None:
    s = streaks(con, today=datetime.now(LOCAL_TZ).date())
    print()
    print("Habits")
    print(f"  longest streak  {s.longest.days:,} days ({s.longest.start} to {s.longest.end})")
    print(f"  current streak  {s.current.days:,} days")

    days = minutes_by(con, "day", window)
    if not days:
        return
    busiest = max(days, key=lambda p: p.minutes)
    print(f"  busiest day     {busiest.start} ({busiest.minutes / 60:,.1f} h)")
    clock = listening_clock(con, window)
    peak = max(clock, key=lambda c: c.minutes)
    print(f"  peak hour       {WEEKDAYS[peak.weekday]} {peak.hour:02d}:00")

    months = minutes_by(con, "month", window)[-12:]
    print()
    print("Hours per month")
    widest = max(p.minutes for p in months)
    for p in months:
        bar = "#" * round(40 * p.minutes / widest)
        print(f"  {p.start:%Y-%m}  {p.minutes / 60:>6,.0f} h  {bar}")


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


def print_behaviour(con: DuckDBPyConnection, window: Window) -> None:
    rate = skip_rate(con, window)
    if rate is None:
        return
    print()
    print(f"Skips: {rate:.0%} of plays ended before 30 seconds")
    print("  most skipped artists (20+ plays)")
    for row in most_skipped(con, "artist", window, limit=3):
        print(f"    {row.name:<32} {row.skip_rate:>4.0%} of {row.plays:,} plays")
    print()
    print("Discovered in this window")
    for d in discoveries(con, window, limit=5):
        print(
            f"  {d.artist_name:<32} first streamed {d.first_played}  {d.streams:>7,} streams since"
        )
    print()
    print("On repeat (most streams of one track in a day)")
    for r in on_repeat(con, window, limit=3):
        label = f"{r.track_name} - {r.artist_name}"
        print(f"  {label[:44]:<44} {r.streams:>3}x on {r.day}")


def print_wrapped(con: DuckDBPyConnection, y: int) -> None:
    w = wrapped(con, y)
    print(f"Your {y} Wrapped")
    print(f"  {w['minutes']:,} minutes listened, {w['totals'].streams:,} streams")
    if w["top_month"]:
        print(f"  biggest month: {w['top_month'].start:%B} ({w['top_month'].minutes / 60:,.0f} h)")
    for kind in ("artists", "tracks", "albums"):
        print()
        print(f"  Top {kind}")
        for rank, row in enumerate(w[f"top_{kind}"], start=1):
            label = row.name if row.artist_name is None else f"{row.name} - {row.artist_name}"
            print(f"    {rank}. {label[:50]:<50} {row.streams:>6,} streams")
    print()
    print("  New to you this year")
    for d in w["discoveries"]:
        print(f"    {d.artist_name} (first streamed {d.first_played:%d %b})")
    if w["on_repeat"]:
        r = w["on_repeat"][0]
        print()
        print(f"  On repeat: {r.track_name} - {r.artist_name}, {r.streams}x on {r.day:%d %b}")


def build(argv: list[str] | None = None) -> None:
    """`build-stats`: compute every stat as JSON documents for one user."""
    parser = argparse.ArgumentParser(description=build.__doc__)
    parser.add_argument("--user", required=True)
    parser.add_argument("--listens", type=Path, default=DEFAULT_PARQUET)
    parser.add_argument("--out", type=Path, help="default: data/stats/<user>.json")
    args = parser.parse_args(argv)
    out = args.out or Path("data/stats") / f"{args.user}.json"

    con = connect(args.listens, materialize=True)
    documents = build_documents(con, args.user, now=datetime.now(UTC))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(documents, indent=1, ensure_ascii=False), encoding="utf-8")
    largest = max(documents.values(), key=lambda d: len(json.dumps(d)))
    print(f"Wrote {len(documents)} stat documents to {out} ({out.stat().st_size / 1e6:,.1f} MB)")
    print(f"  largest: {largest['stat_name']} ({len(json.dumps(largest)) / 1e3:,.0f} KB)")

import json
import logging
from datetime import UTC, date, datetime

import boto3
import httpx

from stats_jobs.concerts import (
    CONCERTS_KEY,
    EVENTS_TTL_S,
    Concerts,
    TicketmasterLimited,
    concerts_document,
    event_summary,
    favourite_artists,
    ticketmaster_fetch,
)
from stats_jobs.job import write_concerts


def tm_event(name, day, status="onsale", city="London"):
    return {
        "name": name,
        "url": f"https://www.ticketmaster.co.uk/{name}",
        "dates": {"start": {"localDate": day, "localTime": "19:30:00"}, "status": {"code": status}},
        "images": [
            {"ratio": "3_2", "width": 640, "url": "https://img/3x2"},
            {"ratio": "16_9", "width": 1024, "url": "https://img/big"},
            {"ratio": "16_9", "width": 640, "url": "https://img/16x9"},
        ],
        "_embedded": {"venues": [{"name": "O2 Academy", "city": {"name": city}}]},
    }


class FakeTicketmaster:
    """Answers like the Discovery API; records every call."""

    def __init__(self, attractions=None, events=None):
        self.attractions = attractions or {}  # keyword -> list of {id, name}
        self.events = events or {}  # attraction id -> list of events
        self.calls = []

    def __call__(self, path, params):
        self.calls.append((path, params))
        if path == "/attractions.json":
            found = self.attractions.get(params["keyword"], [])
            return {"_embedded": {"attractions": found}} if found else {}
        found = self.events.get(params["attractionId"], [])
        return {"_embedded": {"events": found}} if found else {}


def fake():
    return FakeTicketmaster(
        attractions={
            "Weston Estate": [
                {"id": "tribute", "name": "Weston Estate Tribute Night"},
                {"id": "K1", "name": "Weston Estate"},
            ],
            "Nova Lane": [{"id": "fest", "name": "Nova Lane Festival"}],
        },
        events={
            "K1": [
                tm_event("Weston Estate Live", "2026-11-14"),
                tm_event("Weston Estate (cancelled)", "2026-11-20", status="cancelled"),
                tm_event("Weston Estate Glasgow", "2026-12-02", city="Glasgow"),
            ]
        },
    )


def test_event_summary_keeps_what_the_app_shows():
    assert event_summary(tm_event("Gig", "2026-11-14")) == {
        "name": "Gig",
        "date": "2026-11-14",
        "time": "19:30:00",
        "venue": "O2 Academy",
        "city": "London",
        "url": "https://www.ticketmaster.co.uk/Gig",
        "image": "https://img/16x9",
    }
    assert event_summary(tm_event("Gig", "2026-11-14", status="cancelled")) is None


def test_only_an_exact_artist_name_matches():
    concerts = Concerts(fake(), clock=lambda: 1000)
    assert concerts.attraction_id("Weston Estate") == "K1"
    assert concerts.attraction_id("Nova Lane") is None  # only a festival with that name


def test_upcoming_skips_cancelled_and_caches_for_a_day():
    tm = fake()
    now = [1000.0]
    concerts = Concerts(tm, clock=lambda: now[0])

    events = concerts.upcoming("Weston Estate")
    assert [e["name"] for e in events] == ["Weston Estate Live", "Weston Estate Glasgow"]
    assert len(tm.calls) == 2

    concerts.upcoming("Weston Estate")
    assert len(tm.calls) == 2  # from the cache

    now[0] += EVENTS_TTL_S + 1
    concerts.upcoming("Weston Estate")
    assert [p for p, _ in tm.calls] == ["/attractions.json", "/events.json", "/events.json"]


def test_unknown_artists_are_not_asked_again_soon():
    tm = fake()
    concerts = Concerts(tm, clock=lambda: 1000)
    assert concerts.upcoming("Nobody") == []
    assert concerts.upcoming("Nobody") == []
    assert len(tm.calls) == 1


def test_the_budget_and_rate_limits_stop_calls():
    tm = fake()
    concerts = Concerts(tm, budget=1, clock=lambda: 1000)
    assert concerts.upcoming("Weston Estate") == []  # found the id, no budget for events
    assert concerts.calls == 1

    def limited(path, params):
        raise TicketmasterLimited(path)

    concerts = Concerts(limited)
    assert concerts.upcoming("Weston Estate") == []
    assert concerts.stopped
    assert not concerts.changed


def test_favourite_artists_keeps_each_artists_best_rank():
    recent = [{"name": "B"}, {"name": "A"}]
    year = [{"name": "A"}, {"name": "C"}, {"name": "b"}]
    assert [(a["name"], a["rank"]) for a in favourite_artists([recent, year])] == [
        ("B", 1),
        ("A", 1),
        ("C", 2),
    ]


def test_concerts_document_lists_touring_favourites_without_past_dates():
    concerts = Concerts(fake(), clock=lambda: 1000)
    artists = [
        {"name": "Nova Lane", "rank": 1},
        {"name": "Weston Estate", "rank": 2, "image": "https://i.scdn.co/w", "url": "spotify"},
    ]
    doc = concerts_document(artists, concerts, date(2026, 11, 15))
    glasgow = tm_event("Weston Estate Glasgow", "2026-12-02", city="Glasgow")
    assert doc == [
        {
            "artist": "Weston Estate",
            "rank": 2,
            "image": "https://i.scdn.co/w",
            "url": "spotify",
            "events": [event_summary(glasgow)],
        }
    ]


def test_ticketmaster_fetch_spaces_calls_and_sends_the_key():
    seen = []

    def answer(request):
        seen.append(request.url)
        if request.url.params["keyword"] == "slow":
            return httpx.Response(429)
        return httpx.Response(200, json={"ok": True})

    sleeps = []
    with httpx.Client(transport=httpx.MockTransport(answer)) as http:
        fetch = ticketmaster_fetch(http, "secret-key", sleep=sleeps.append, clock=lambda: 10.0)
        assert fetch("/attractions.json", {"keyword": "a"}) == {"ok": True}
        fetch("/attractions.json", {"keyword": "b"})
        try:
            fetch("/attractions.json", {"keyword": "slow"})
            raise AssertionError("expected TicketmasterLimited")
        except TicketmasterLimited:
            pass
    assert seen[0].params["apikey"] == "secret-key"
    assert sleeps == [0.25, 0.25]


def test_write_concerts_reads_top_artists_and_saves_the_cache(aws):
    stats = boto3.resource("dynamodb").Table("stats")
    for name, rows in {
        "top_artists#4_weeks": [{"name": "Weston Estate"}],
        "top_artists#12_months": [{"name": "Nova Lane"}],
    }.items():
        stats.put_item(Item={"user_id": "u1", "stat_name": name, "data": json.dumps(rows)})
    s3 = boto3.client("s3")
    concerts = Concerts.load(s3, "data", fake())

    touring = write_concerts(
        "u1", stats_table=stats, concerts=concerts, now=datetime(2026, 10, 29, 12, tzinfo=UTC)
    )

    assert touring == 1
    doc = json.loads(stats.get_item(Key={"user_id": "u1", "stat_name": "concerts"})["Item"]["data"])
    assert doc[0]["artist"] == "Weston Estate"
    concerts.save(s3, "data")
    cached = json.loads(s3.get_object(Bucket="data", Key=CONCERTS_KEY)["Body"].read())
    assert cached["attractions"]["weston estate"]["id"] == "K1"
    assert Concerts.load(s3, "data", fake()).events["K1"]["events"]


def test_the_key_never_reaches_the_logs(caplog):
    caplog.set_level(logging.DEBUG)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={}))
    with httpx.Client(transport=transport) as http:
        ticketmaster_fetch(http, "secret-key", sleep=lambda s: None)("/events.json", {})
    assert "secret-key" not in caplog.text

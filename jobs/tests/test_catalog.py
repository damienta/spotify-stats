import boto3

from stats_jobs.catalog import CATALOG_KEY, Catalog, RateLimited, enrich, pick_image


def image(width):
    return {"url": f"https://i.scdn.co/{width}", "width": width, "height": width}


TRACK = {
    "external_urls": {"spotify": "https://open.spotify.com/track/t1"},
    "album": {
        "external_urls": {"spotify": "https://open.spotify.com/album/al1"},
        "images": [image(640), image(300), image(64)],
    },
    "artists": [{"id": "feat", "name": "Featured"}, {"id": "a1", "name": "Weston Estate"}],
}
ARTIST = {
    "external_urls": {"spotify": "https://open.spotify.com/artist/a1"},
    "images": [image(320)],
}


class FakeSpotify:
    def __init__(self, missing=(), limited=False):
        self.calls = []
        self.missing = set(missing)
        self.limited = limited

    def __call__(self, path):
        self.calls.append(path)
        if self.limited:
            raise RateLimited("wait")
        if path in self.missing:
            return None
        return TRACK if path.startswith("/tracks/") else ARTIST


def test_pick_image_prefers_the_smallest_big_enough():
    assert pick_image([image(640), image(300), image(64)]) == "https://i.scdn.co/300"
    assert pick_image([image(64)]) == "https://i.scdn.co/64"
    assert pick_image([]) is None


def test_tracks_albums_and_artists_get_pictures_and_links():
    catalog = Catalog(FakeSpotify())

    assert catalog.describe("track", "t1", None) == {
        "image": "https://i.scdn.co/300",
        "url": "https://open.spotify.com/track/t1",
    }
    assert catalog.describe("album", "t1", None)["url"].endswith("/album/al1")
    # The row's own artist, not the one featured first on the track.
    assert catalog.describe("artist", "t1", "Weston Estate") == {
        "image": "https://i.scdn.co/320",
        "url": "https://open.spotify.com/artist/a1",
    }


def test_each_item_is_looked_up_once():
    spotify = FakeSpotify()
    catalog = Catalog(spotify)

    for _ in range(3):
        catalog.describe("artist", "t1", "Weston Estate")

    assert spotify.calls == ["/tracks/t1", "/artists/a1"]


def test_unknown_ids_are_remembered_and_rows_without_ids_skipped():
    spotify = FakeSpotify(missing={"/tracks/gone"})
    catalog = Catalog(spotify)

    assert catalog.describe("track", "gone", None) == {}
    assert catalog.describe("track", "gone", None) == {}
    assert catalog.describe("track", None, None) == {}
    assert spotify.calls == ["/tracks/gone"]


def test_lookups_stop_at_the_budget_or_when_rate_limited():
    within_budget = Catalog(FakeSpotify(), budget=1)
    within_budget.describe("track", "t1", None)
    assert within_budget.describe("track", "t2", None) == {}

    limited = FakeSpotify(limited=True)
    catalog = Catalog(limited)
    catalog.describe("track", "t1", None)
    catalog.describe("track", "t2", None)
    assert len(limited.calls) == 1


def doc(stat_name, data):
    return {"stat_name": stat_name, "data": data}


def test_enrich_fills_top_lists_and_wrapped_recent_windows_first():
    spotify = FakeSpotify()
    documents = {
        "top_tracks#year_2020": doc("top_tracks#year_2020", [{"track_id": "old"}]),
        "top_tracks#4_weeks": doc("top_tracks#4_weeks", [{"track_id": "new"}]),
        "wrapped#2025": doc("wrapped#2025", {"top_albums": [{"track_id": "w"}]}),
        "totals#4_weeks": doc("totals#4_weeks", {"streams": 1}),
    }

    pictured = enrich(documents, Catalog(spotify))

    assert pictured == 3
    assert spotify.calls[0] == "/tracks/new"
    assert documents["wrapped#2025"]["data"]["top_albums"][0]["image"] == "https://i.scdn.co/300"
    assert documents["totals#4_weeks"]["data"] == {"streams": 1}


def test_catalog_is_saved_to_and_loaded_from_s3(aws):
    s3 = boto3.client("s3")
    spotify = FakeSpotify()
    catalog = Catalog.load(s3, "data", spotify)
    catalog.describe("track", "t1", None)
    catalog.save(s3, "data")

    again = FakeSpotify()
    reloaded = Catalog.load(s3, "data", again)
    reloaded.describe("track", "t1", None)

    assert again.calls == []
    assert s3.head_object(Bucket="data", Key=CATALOG_KEY)["ContentType"] == "application/json"


def test_every_lists_number_one_comes_before_any_number_two():
    spotify = FakeSpotify()
    documents = {
        "top_albums#4_weeks": doc("top_albums#4_weeks", [{"track_id": "a1"}, {"track_id": "a2"}]),
        "top_tracks#6_months": doc("top_tracks#6_months", [{"track_id": "t1"}]),
        "on_repeat#4_weeks": doc("on_repeat#4_weeks", [{"track_id": "r1", "track_name": "x"}]),
    }

    enrich(documents, Catalog(spotify, budget=3))

    assert sorted(spotify.calls) == ["/tracks/a1", "/tracks/r1", "/tracks/t1"]
    assert "image" in documents["on_repeat#4_weeks"]["data"][0]


def test_discoveries_get_the_artists_picture():
    documents = {
        "discoveries#4_weeks": doc(
            "discoveries#4_weeks", [{"artist_name": "Weston Estate", "track_id": "t1"}]
        )
    }

    enrich(documents, Catalog(FakeSpotify()))

    assert documents["discoveries#4_weeks"]["data"][0]["url"].endswith("/artist/a1")

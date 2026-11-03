from stats_api.friends import both_love, new_to_you, taste_match


def rows(*pairs):
    return [{"name": name, "hours": hours} for name, hours in pairs]


def test_identical_lists_match_100():
    a = rows(("Nova", 10), ("Kites", 5))
    assert taste_match(a, a) == 100


def test_same_artists_in_the_same_proportions_match_100_whatever_the_hours():
    assert taste_match(rows(("Nova", 10), ("Kites", 5)), rows(("nova", 2), ("Kites", 1))) == 100


def test_disjoint_lists_match_0():
    assert taste_match(rows(("Nova", 10)), rows(("Kites", 10))) == 0


def test_sharing_your_favourite_counts_more_than_a_minor_one():
    mine = rows(("Nova", 90), ("Kites", 10))
    assert taste_match(mine, rows(("Nova", 50), ("Other", 50))) > taste_match(
        mine, rows(("Kites", 50), ("Other", 50))
    )


def test_nothing_to_compare_is_none():
    assert taste_match([], rows(("Nova", 1))) is None
    assert taste_match(rows(("Nova", 0)), rows(("Nova", 1))) is None


def test_both_love_puts_artists_you_both_rank_highly_first():
    mine = rows(("A", 9), ("B", 8), ("C", 7))
    theirs = rows(("C", 9), ("B", 8), ("A", 1))
    assert [r["name"] for r in both_love(mine, theirs)] == ["B", "A", "C"]


def test_new_to_you_keeps_their_order_and_a_limit():
    theirs = rows(*((f"X{n}", 1) for n in range(30)))
    picks = new_to_you(theirs, rows(("X0", 1)), limit=3)
    assert [r["name"] for r in picks] == ["X1", "X2", "X3"]

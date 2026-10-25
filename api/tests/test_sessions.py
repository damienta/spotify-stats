import pytest

from stats_api.sessions import InvalidToken, sign, verify


def test_round_trip():
    token = sign("secret", {"sub": "u1"}, "session", ttl_s=60, now=1_000)

    assert verify("secret", token, "session", now=1_030)["sub"] == "u1"


@pytest.mark.parametrize(
    ("secret", "purpose", "now", "reason"),
    [
        ("other", "session", 1_030, "bad signature"),
        ("secret", "state", 1_030, "bad signature"),  # a session token isn't valid OAuth state
        ("secret", "session", 1_061, "expired"),
    ],
)
def test_rejects(secret, purpose, now, reason):
    token = sign("secret", {"sub": "u1"}, "session", ttl_s=60, now=1_000)

    with pytest.raises(InvalidToken, match=reason):
        verify(secret, token, purpose, now=now)


def test_tampered_payload_is_rejected():
    token = sign("secret", {"sub": "u1"}, "session", ttl_s=60)
    payload, signature = token.split(".")
    forged = sign("secret", {"sub": "admin"}, "session", ttl_s=60).split(".")[0]

    with pytest.raises(InvalidToken):
        verify("secret", f"{forged}.{signature}", "session")

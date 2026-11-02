"""Friendships, stored as one item per direction in the friends table.

`alice -> bob` and `bob -> alice` are written and deleted together in one transaction, so
"my friends" is a single Query on my own partition and a friendship is never one-sided.
See docs/plans/friends.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

# Keeps the leaderboard to one BatchGetItem (100 keys) and the friends list short.
MAX_FRIENDS = 50
INVITE_TTL_S = 14 * 24 * 3600


class AlreadyFriends(Exception):
    pass


class NotFriends(Exception):
    pass


@dataclass(frozen=True)
class Friendship:
    friend_id: str
    since: str


class FriendsTable:
    def __init__(self, table: Any) -> None:
        self.table = table

    def get(self, user_id: str, friend_id: str) -> Friendship | None:
        item = self.table.get_item(Key={"user_id": user_id, "friend_id": friend_id}).get("Item")
        return Friendship(item["friend_id"], item["since"]) if item else None

    def of(self, user_id: str) -> list[Friendship]:
        items, kwargs = [], {}
        while True:
            page = self.table.query(
                KeyConditionExpression="user_id = :u",
                ExpressionAttributeValues={":u": user_id},
                **kwargs,
            )
            items.extend(page["Items"])
            if "LastEvaluatedKey" not in page:
                return [Friendship(i["friend_id"], i["since"]) for i in items]
            kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    def count(self, user_id: str) -> int:
        response = self.table.query(
            KeyConditionExpression="user_id = :u",
            ExpressionAttributeValues={":u": user_id},
            Select="COUNT",
        )
        return int(response["Count"])

    def add(self, a: str, b: str, now: datetime | None = None) -> str:
        """Both directions or neither. A double tap fails the condition on the second try."""
        since = (now or datetime.now(UTC)).isoformat(timespec="seconds")
        try:
            self.table.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table.name,
                            "Item": {"user_id": x, "friend_id": y, "since": since},
                            "ConditionExpression": "attribute_not_exists(friend_id)",
                        }
                    }
                    for x, y in ((a, b), (b, a))
                ]
            )
        except self.table.meta.client.exceptions.TransactionCanceledException as e:
            raise AlreadyFriends from e
        return since

    def remove(self, a: str, b: str) -> None:
        """Deletes both directions. Only `a`'s side must exist, so this also clears a
        half-friendship if one is ever left behind."""
        try:
            self.table.meta.client.transact_write_items(
                TransactItems=[
                    {
                        "Delete": {
                            "TableName": self.table.name,
                            "Key": {"user_id": a, "friend_id": b},
                            "ConditionExpression": "attribute_exists(friend_id)",
                        }
                    },
                    {
                        "Delete": {
                            "TableName": self.table.name,
                            "Key": {"user_id": b, "friend_id": a},
                        }
                    },
                ]
            )
        except self.table.meta.client.exceptions.TransactionCanceledException as e:
            raise NotFriends from e

    def remove_all(self, user_id: str) -> int:
        """Every friendship of a user, both directions: for DELETE /me."""
        friends = self.of(user_id)
        for f in friends:
            self.table.delete_item(Key={"user_id": f.friend_id, "friend_id": user_id})
            self.table.delete_item(Key={"user_id": user_id, "friend_id": f.friend_id})
        return len(friends)


# Comparing tastes. Lists are `top_artists` documents: rows with `name`, `hours`, and the
# catalogue's `image` and `url` once the stats job has looked them up.

SHOWN = 10


def name_key(name: str) -> str:
    """Case and spacing don't make two artists different (as in stats_jobs.concerts)."""
    return " ".join(name.casefold().split())


def public_row(row: dict[str, Any]) -> dict[str, Any]:
    """The parts of a top-list row a friend may see: what it is, not how much was played."""
    return {
        "name": row.get("name"),
        "artist_name": row.get("artist_name"),
        "image": row.get("image"),
        "url": row.get("url"),
    }


def _shares(rows: list[dict[str, Any]]) -> dict[str, float]:
    hours: dict[str, float] = {}
    for row in rows:
        key = name_key(row.get("name") or "")
        if key:
            hours[key] = hours.get(key, 0.0) + float(row.get("hours") or 0)
    total = sum(hours.values())
    return {k: h / total for k, h in hours.items()} if total else {}


def taste_match(mine: list[dict[str, Any]], theirs: list[dict[str, Any]]) -> int | None:
    """Weighted Jaccard of the two lists, 0-100: each artist counts by its share of the
    user's listening, so sharing your number one matters more than sharing your 90th.
    None when either side has nothing to compare yet."""
    a, b = _shares(mine), _shares(theirs)
    if not a or not b:
        return None
    keys = a.keys() | b.keys()
    overlap = sum(min(a.get(k, 0.0), b.get(k, 0.0)) for k in keys)
    union = sum(max(a.get(k, 0.0), b.get(k, 0.0)) for k in keys)
    return round(100 * overlap / union)


def both_love(
    mine: list[dict[str, Any]], theirs: list[dict[str, Any]], limit: int = SHOWN
) -> list[dict[str, Any]]:
    """Artists in both lists, best first: ordered by the worse of the two ranks, so an artist
    you both rank highly beats one that's your number one and their 90th."""
    yours = {name_key(r["name"]): (rank, r) for rank, r in enumerate(mine, 1) if r.get("name")}
    shared = []
    for their_rank, row in enumerate(theirs, 1):
        found = yours.pop(name_key(row.get("name") or ""), None)
        if found:
            your_rank, my_row = found
            pictured = row if row.get("image") else my_row
            shared.append(
                {**public_row(pictured), "your_rank": your_rank, "their_rank": their_rank}
            )
    # Ties go to your own favourite: it's your screen.
    shared.sort(key=lambda r: (max(r["your_rank"], r["their_rank"]), r["your_rank"]))
    return shared[:limit]


def new_to_you(
    theirs: list[dict[str, Any]], known: list[dict[str, Any]], limit: int = SHOWN
) -> list[dict[str, Any]]:
    """Their top artists, in their order, that aren't in any of your lists."""
    seen = {name_key(r.get("name") or "") for r in known}
    picks = [public_row(r) for r in theirs if name_key(r.get("name") or "") not in seen]
    return picks[:limit]

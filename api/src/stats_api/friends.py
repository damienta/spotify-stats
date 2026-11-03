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

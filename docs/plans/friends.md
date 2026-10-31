# Plan: friends

How to add friends to Stats: connect by invite link, see a friend's summary, compare tastes
and a weekly minutes leaderboard. Written 31 October 2026, before any of it is built. Read
[../HANDOFF.md](../HANDOFF.md) first for how the project runs.

## What it does

1. **Invite.** In the Friends tab you copy (or share) your invite link,
   `https://<site>/add/<invite>`.
2. **Accept.** Your friend opens it, logs in with Spotify if they need to, and taps "Add".
   You're now friends both ways. No requests to approve: having the link is the approval.
3. **See their summary.** Top 10 artists and tracks (4 weeks), minutes this week, current streak.
   Never their full history, recent plays or listening clock.
4. **Compare.** A taste match % from how much your top artists overlap, artists you both love,
   and theirs you've never played.
5. **Leaderboard.** You and your friends ranked by minutes this week.
6. **Control.** "Share my summary with friends" in Settings (on by default), remove a friend at
   any time, and "Delete my data" removes every friendship too.

**Limit while Spotify keeps the app in development mode:** only the 25 people added under
Users Management in the [Spotify dashboard](https://developer.spotify.com/dashboard) can log in
at all ([quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes)).
Friends works within that; growing past it needs the quota extension.

## How it fits the existing code

Everything follows patterns already in the repo, so there are no new AWS services.

| Need | Reuse | Where |
|---|---|---|
| Invite links that can't be forged and expire | `sign` / `verify` with a new purpose, `"invite"` | [`api/src/stats_api/sessions.py`](https://github.com/damienta/spotify-stats/blob/main/api/src/stats_api/sessions.py) |
| Who is calling | `current_user` / `UserIdDep` | [`api/src/stats_api/app.py`](https://github.com/damienta/spotify-stats/blob/main/api/src/stats_api/app.py) |
| A friend's stats | the precomputed documents in the stats table (`top_artists#4_weeks`, `totals#this_week`, ...) | [`jobs/src/stats_jobs/documents.py`](https://github.com/damienta/spotify-stats/blob/main/jobs/src/stats_jobs/documents.py) |
| Removing a user everywhere | `DELETE /me` (`delete_me`) | [`api/src/stats_api/app.py`](https://github.com/damienta/spotify-stats/blob/main/api/src/stats_api/app.py) |
| Users table helper style | `UsersTable` | [`ingest/src/stats_ingest/storage.py`](https://github.com/damienta/spotify-stats/blob/main/ingest/src/stats_ingest/storage.py) |
| Tables, IAM | `aws_dynamodb_table`, the API role's policy document | [`infra/live/dynamodb.tf`](https://github.com/damienta/spotify-stats/blob/main/infra/live/dynamodb.tf), [`infra/live/lambda_api.tf`](https://github.com/damienta/spotify-stats/blob/main/infra/live/lambda_api.tf) |
| API tests with fake AWS | moto fixtures, `TestClient` | [`api/tests/test_app.py`](https://github.com/damienta/spotify-stats/blob/main/api/tests/test_app.py) |
| Web data fetching | `useStat`, `api()` | [`web/src/lib/queries.ts`](https://github.com/damienta/spotify-stats/blob/main/web/src/lib/queries.ts), [`web/src/lib/api.ts`](https://github.com/damienta/spotify-stats/blob/main/web/src/lib/api.ts) |
| A new tab | `Tab`, `TABS`, `go()` | [`web/src/components/Nav.tsx`](https://github.com/damienta/spotify-stats/blob/main/web/src/components/Nav.tsx), [`web/src/App.tsx`](https://github.com/damienta/spotify-stats/blob/main/web/src/App.tsx) |
| Made-up data for `/?demo` | `demoApi` | [`web/src/lib/demo.ts`](https://github.com/damienta/spotify-stats/blob/main/web/src/lib/demo.ts) |

## Data

### New table: `spotify-stats-friends`

One item per direction, so "my friends" is a single query on my own partition:

| user_id (hash) | friend_id (range) | since |
|---|---|---|
| alice | bob | 2026-11-02T18:00:00Z |
| bob | alice | 2026-11-02T18:00:00Z |

- Both items are written together with `TransactWriteItems`, each with
  `attribute_not_exists(friend_id)`, so a double tap can't half-create a friendship.
- Removing deletes both items in one transaction.
- Cap at 50 friends: count with a `Query` (`Select=COUNT`) before accepting.
- Provisioned 2 read / 2 write like the users table; deletion protection on.

### Users table: two new attributes

- `share_with_friends` (bool, missing means true).
- `invite_nonce` (string). Put inside every invite; "Reset my link" changes it, which kills
  every link given out before. Created on first `GET /friends/invite`.

No new attribute is needed for a friend's stats: they're read from the stats table by their
`user_id`.

## API

All under the existing FastAPI app. `me` is always `current_user`; never trust an id from the
body for "who am I".

| Method and path | Does | Errors |
|---|---|---|
| `GET /friends/invite` | Returns `{url}` with `sign(secret, {"sub": me, "n": invite_nonce}, "invite", 14 days)` | |
| `POST /friends/invite/reset` | New `invite_nonce`; returns the new link | |
| `GET /friends/invite/{invite}` | Who the link is from (display name), so the page can say "Add Alice?" | 404 bad/expired/reset link |
| `POST /friends` `{invite}` | Verify, check nonce still matches, not yourself, inviter exists, under the cap; write both items | 400 own link, 404 bad link, 409 already friends, 422 cap |
| `GET /friends` | `[{user_id, display_name, since, minutes_this_week}]` | |
| `DELETE /friends/{id}` | Delete both items | 404 not friends |
| `GET /friends/{id}/summary` | Their top 10s, minutes this week, streak | **404 if not friends or they've turned sharing off** |
| `GET /friends/{id}/compare` | Taste match %, shared artists, theirs-not-yours | same as summary |
| `GET /friends/leaderboard` | Me and my sharing friends by minutes this week | |
| `PATCH /me` `{share_with_friends}` | The Settings switch | |

**The one rule that matters:** every `/friends/{id}/...` route first checks that the item
`(me, id)` exists in the friends table, and that `id` shares, and returns **404** (not 403) if
not, so nobody can even learn whether a user id exists. Put this in one dependency
(`FriendDep`) and use it on every route, rather than repeating the check. This is the
"broken access control" problem in the
[OWASP Top 10](https://owasp.org/Top10/A01_2021-Broken_Access_Control/).

`DELETE /me` gains: query my friends, delete both items for each, then everything it already
deletes.

### Taste match

On the two users' `top_artists#12_months` lists (top 100 by minutes):

- **Weighted Jaccard:** for each artist, `min(share_a, share_b)` summed, divided by
  `max(share_a, share_b)` summed, where `share` is that artist's fraction of the user's top-100
  minutes. 0% means nothing in common, 100% means identical.
- Artists are matched on Spotify artist id when both rows have one, else the case-folded name
  (as `_name_key` does in
  [`jobs/src/stats_jobs/concerts.py`](https://github.com/damienta/spotify-stats/blob/main/jobs/src/stats_jobs/concerts.py)).
- "You both love": shared artists sorted by the smaller of the two ranks. "Theirs, new to you":
  their top 20 not in your list.
- Background: [Jaccard index](https://en.wikipedia.org/wiki/Jaccard_index).

Compute it in the API request (two `GetItem`s and some arithmetic, well under 100 ms). Only
precompute it in the stats job if it ever gets slow.

## Web

- **Friends tab** (fifth tab, `Users` icon). Bottom bar on phones still fits five.
  - Empty state: "Add your first friend" and the invite card.
  - Invite card: "Copy link", plus "Share" through `navigator.share` on phones.
  - Leaderboard for this week, then the friends list.
- **Friend page** (opens from the list, back button, no new tab): their summary, the taste
  match ring, "You both love", "Theirs, new to you", "Remove friend" with a confirm like
  "Delete my data".
- **`/add/<invite>`**: handled before the login check, like `/privacy` in `App.tsx`.
  - Logged out: save the invite in `sessionStorage`, show "Alice invited you. Log in with
    Spotify to add them", and after login (`finishLogin`) send it to `POST /friends`.
  - Logged in: "Add Alice?" with Add / Not now.
- **Settings:** "Share my summary with friends" switch, "Reset my invite link".
- **Demo mode:** three made-up friends in `demo.ts` so `/?demo` shows the whole feature.
- **Privacy page:** must change in the same PR as the API. It currently says nobody else can
  see your stats; it should say friends you add can see your summary, which parts, and how to
  turn it off.

## Build order (one PR each, Terraform in its own commit)

1. **Infra:** friends table; API role gets `GetItem`, `PutItem`, `DeleteItem`, `Query`,
   `ConditionCheckItem` on it (transactions need the item-level actions); `FRIENDS_TABLE` env
   var. `terraform plan`, then apply only on Damien's "apply".
2. **API, connecting:** invite, reset, preview, accept, list, remove, `DELETE /me` cleanup,
   `PATCH /me`. Tests:
   - accepting writes both directions; accepting twice gives 409
   - your own link gives 400; an expired, forged or reset link gives 404
   - remove deletes both directions
   - `DELETE /me` leaves no friend items pointing at you
3. **API, seeing:** `FriendDep`, summary, compare, leaderboard. Tests:
   - not friends gives 404
   - friends but sharing off gives 404 and they're left out of the leaderboard
   - taste match: identical lists give 100, disjoint lists give 0
   - a friend's summary never includes fields beyond the agreed ones (assert the exact keys)
4. **Web:** the tab, the friend page, `/add/...`, Settings, demo data, privacy page.
5. **Docs:** README API table, architecture/decisions ("friends: invite links, two-way items,
   404 not 403"), HANDOFF.

Each PR: `uv run pytest`, `uv run ruff check .`, `cd web && npm run lint && npm run build`, try
it in `/?demo`, then real data after deploy with a second Spotify account added to the
dashboard's user list.

## References

- Spotify: [quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes),
  [Developer Policy](https://developer.spotify.com/policy) (what can be shown to whom),
  [Design guidelines](https://developer.spotify.com/documentation/design).
- DynamoDB: [transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html),
  [condition expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html),
  [many-to-many / adjacency lists](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-adjacency-graphs.html).
- Terraform: [`aws_dynamodb_table`](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/dynamodb_table).
- FastAPI: [dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) (for `FriendDep`).
- Testing AWS: [moto](https://docs.getmoto.org/en/latest/).
- Web: [Web Share API](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/share).
- Security: [OWASP broken access control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/).

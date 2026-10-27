# Caching: how pictures and links work

The short version: **we ask Spotify about each track and artist once, ever, write the answer
down in one shared file, and copy it into everyone's stats.** The app never asks Spotify for a
picture itself.

## The problem

Your plays only say *what* you played: a track ID and some names. They don't include album
covers, artist photos or links. Those live in Spotify's catalogue, and Spotify limits how often
this app (in development mode) may ask:

- one item per request (bulk lookups of 50 are refused with 403)
- roughly 800 lookups before Spotify says "wait" for nearly a day (`Retry-After: 84797`)
- no genres any more

So asking Spotify every time someone opens the app is out of the question. We need to remember
the answers.

## Three layers of caching

```
          Spotify catalogue                  (asked once per item, ever)
                 │
                 ▼
   S3  catalog/spotify.json                  the shared cache: id → picture, link
                 │   copied in by the stats job, hourly
                 ▼
   DynamoDB stat documents                   each top-list row carries its image + url
                 │   one read per screen
                 ▼
   The app (TanStack Query, 5 minutes)       the browser keeps documents for 5 minutes
                 │
                 ▼
   <img src="https://i.scdn.co/...">         the picture itself, straight from Spotify's servers
```

### 1. The catalogue file (shared by everyone)

`s3://spotify-stats-data-…/catalog/spotify.json`:

```json
{
  "tracks":  { "<track id>":  { "image": "…", "url": "…", "album_url": "…",
                               "artists": [{ "id": "…", "name": "…" }] } },
  "artists": { "<artist id>": { "image": "…", "url": "…" } },
  "paused_until": 1793211255
}
```

- **Tracks** give the album cover, the track and album links, and the artists' IDs.
- **Artists** give the artist photo and link. Plays only store artist *names*, so we find an
  artist's ID through their most-played track.
- An ID Spotify doesn't know is stored as `null`, so it isn't asked about again.
- `paused_until` remembers Spotify's "wait" so no run asks before then.

### 2. The stat documents

Every hour the stats job builds each user's documents, then for every row in the top lists,
on repeat and new to you:

1. Look the row's track (and artist) up in the catalogue file.
2. If it's there, copy `image` and `url` into the row. **No Spotify call.**
3. If not, ask Spotify (up to 500 a run), add the answer to the file, and copy it in.

Then it saves the documents to DynamoDB and the file back to S3. The order matters: #1 of every
recent list first, then every #2, and so on, past years last, so the rows people actually see
get pictures first.

### 3. The browser

The app keeps each document for 5 minutes, so switching tabs doesn't refetch. The image files
come from Spotify's CDN, and the browser caches those like any other picture.

## Does it work for other people?

**Yes, and it gets better with more users.** The catalogue file is one file for everyone.

- If you and a friend both listen to Weston Estate, the first of you to have stats built pays
  the lookup. Everyone after gets the picture for free.
- Popular artists and tracks rarely change, so once they're in the file they stay.
- A new user only costs lookups for the music nobody else has listened to.

**The catch for new users:** someone with years of unusual music could need hundreds of new
lookups. Their stats appear within the hour, but some pictures may take a day or two while the
Spotify limit recovers. Initials show in the meantime.

## Ways it could improve

1. **A steady queue instead of bursts.** A small separate Lambda takes one missing item every
   few seconds. Spotify limits bursts, so a gentle steady rate should avoid the day-long wait.
2. **New users first.** Spend lookups on a new user's top 10s before anyone's deep ranks.
3. **Look up on demand.** If the app shows a row without a picture, the API looks up just that
   one.
4. **Refresh old entries.** Artists change photos; re-check entries older than a few months.
5. **Genres from elsewhere.** Last.fm or MusicBrainz, cached the same way.

## Why not store the images ourselves?

Spotify's terms want its artwork shown from its own servers, and storing copies would cost
storage and bandwidth for no gain. We store the *address* (`https://i.scdn.co/…`), which is
tiny and rarely changes.
